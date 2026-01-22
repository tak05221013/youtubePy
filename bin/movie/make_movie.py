import json
import os
import sys
from moviepy import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

# ==========================================
# 1. 環境設定
# ==========================================
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==========================================
# 2. テロップのスタイル定義（基本の最大サイズ）
# ==========================================
STYLES = {
    "impact_red": {
        "fontsize": 110,  # 基本は大きく
        "color": "white",
        "bg_color": "red",
        "font": "BIZ-UDGothicB.ttc",
    },
    "caption_white": {
        "fontsize": 75,  # 基本は大きく
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 2,
        "font": "BIZ-UDGothicB.ttc",
    }
}


def resolve_path(file_path, base_dir):
    if not file_path or not base_dir:
        return file_path
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(base_dir, file_path)


def calculate_optimized_fontsize(text, base_fontsize, target_width):
    """
    テキストがターゲット幅に収まるようにフォントサイズを調整する関数
    """
    if not text:
        return base_fontsize

    # テキストの中で一番長い行の文字数を取得
    lines = text.split('\n')
    max_char_count = max(len(line) for line in lines) if lines else 0

    if max_char_count == 0:
        return base_fontsize

    # 簡易計算: 幅 / 文字数 = 1文字あたりの最大ピクセル数
    # 少し余裕を持たせるために 0.95 を掛ける
    calculated_size = int((target_width / max_char_count) * 0.95)

    # 設定値より小さくなる場合（文字が多い場合）のみ採用する
    return min(base_fontsize, calculated_size)


def create_video_from_json(json_path, image_base_dir=None, audio_base_dir=None, bgm_base_dir=None,
                           output_base_dir=None):
    if not os.path.exists(json_path):
        print(f"Error: JSON file '{json_path}' not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    settings = data['project_settings']
    scene_clips = []

    print("--- シーンの生成開始 ---")
    for i, s in enumerate(data['scenes']):
        print(f"Scene {i + 1}/{len(data['scenes'])} を処理中...")

        audio_path = resolve_path(s['narration']['audio_path'], audio_base_dir)
        if not os.path.exists(audio_path):
            print(f"Warning: Audio '{audio_path}' not found. Skipping scene.")
            continue

        audio = AudioFileClip(audio_path)
        duration = audio.duration

        img_path = resolve_path(s['image_path'], image_base_dir)
        if not os.path.exists(img_path):
            print(f"Warning: Image '{img_path}' not found. Skipping.")
            continue

        img = ImageClip(img_path).with_duration(duration)
        img = img.resized(width=settings['width'])

        if s.get('animation') == 'zoom_in':
            img = img.resized(lambda t: 1.0 + 0.1 * (t / duration))

        img = img.with_position('center')

        sub_clips = [img]
        for sub in s.get('subtitles', []):
            style = STYLES.get(sub['style'], STYLES['caption_white'])
            sub_duration = sub.get('duration', duration - sub['start_offset'])

            # 修正ポイント1: テロップエリアの幅を 80% -> 90% に拡大
            target_width = int(settings['width'] * 0.9)

            # 修正ポイント2: 文字数に応じてフォントサイズを自動計算
            optimized_size = calculate_optimized_fontsize(
                sub['text'],
                style['fontsize'],
                target_width
            )

            txt = TextClip(
                text=sub['text'],
                font=style['font'],
                font_size=optimized_size,  # 計算済みのサイズを適用
                color=style['color'],
                bg_color=style.get('bg_color'),
                stroke_color=style.get('stroke_color'),
                stroke_width=style.get('stroke_width', 0),
                method='caption',
                size=(target_width, None)  # 幅指定は維持（念のため）
            )

            txt = (txt.with_start(sub['start_offset'])
                   .with_duration(sub_duration)
                   .with_position(tuple(sub['position'])))
            sub_clips.append(txt)

        scene_video = CompositeVideoClip(sub_clips, size=(settings['width'], settings['height']))
        scene_video = scene_video.with_audio(audio).with_duration(duration)

        scene_clips.append(scene_video)

    if not scene_clips:
        print("Error: 有効なシーンがありません。")
        return

    final_video = concatenate_videoclips(scene_clips, method="compose")

    bgm_path = resolve_path(settings.get('bgm_path'), bgm_base_dir)
    if bgm_path and os.path.exists(bgm_path):
        bgm = AudioFileClip(bgm_path).with_volume_scaled(settings['bgm_volume'])
        bgm = bgm.with_duration(final_video.duration)

        from moviepy.audio.AudioClip import CompositeAudioClip
        combined_audio = CompositeAudioClip([final_video.audio, bgm])
        final_video = final_video.with_audio(combined_audio)

    output_path = resolve_path(settings.get('output_file', 'output_shorts.mp4'), output_base_dir)
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"--- 書き出し開始: {output_path} ---")
    final_video.write_videofile(
        output_path,
        fps=settings.get('fps', 30),
        codec="libx264",
        audio_codec="aac"
    )
    print("--- 完了 ---")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_input = sys.argv[1]
        image_base_dir = sys.argv[2] if len(sys.argv) > 2 else None
        audio_base_dir = sys.argv[3] if len(sys.argv) > 3 else None
        bgm_base_dir = sys.argv[4] if len(sys.argv) > 4 else None
        output_base_dir = sys.argv[5] if len(sys.argv) > 5 else None
        create_video_from_json(json_input, image_base_dir, audio_base_dir, bgm_base_dir, output_base_dir)
    else:
        print("使い方: python make_movie.py [設定JSONファイル名] ...")