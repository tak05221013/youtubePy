import json
import os
import sys
from moviepy import ImageClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_videoclips

# ==========================================
# 1. 環境設定 (ImageMagickのパスを指定)
# ==========================================
# ImageMagickのパスを環境変数にセット
os.environ["IMAGEMAGICK_BINARY"] = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"

# ==========================================
# 2. テロップのスタイル定義
# ==========================================
STYLES = {
    "impact_red": {
        "fontsize": 80,
        "color": "white",
        "bg_color": "red",
        "font": "BIZ-UDGothicB.ttc",
    },
    "caption_white": {
        "fontsize": 60,
        "color": "white",
        "stroke_color": "black",
        "stroke_width": 2,
        "font": "BIZ-UDGothicB.ttc",
    }
}


def create_video_from_json(json_path):
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

        audio_path = s['narration']['audio_path']
        if not os.path.exists(audio_path):
            print(f"Warning: Audio '{audio_path}' not found. Skipping scene.")
            continue

        audio = AudioFileClip(audio_path)
        duration = audio.duration

        img_path = s['image_path']
        if not os.path.exists(img_path):
            print(f"Warning: Image '{img_path}' not found. Skipping.")
            continue

        # v2.x対応: with_duration
        img = ImageClip(img_path).with_duration(duration)
        img = img.resized(width=settings['width'])

        if s.get('animation') == 'zoom_in':
            img = img.resized(lambda t: 1.0 + 0.1 * (t / duration))

        # v2.x対応: with_position
        img = img.with_position('center')

        sub_clips = [img]
        for sub in s.get('subtitles', []):
            style = STYLES.get(sub['style'], STYLES['caption_white'])
            sub_duration = sub.get('duration', duration - sub['start_offset'])

            # 修正ポイント: sizeの計算結果を int() で囲んで整数化
            target_width = int(settings['width'] * 0.8)

            txt = TextClip(
                text=sub['text'],
                font=style['font'],
                font_size=style['fontsize'],
                color=style['color'],
                bg_color=style.get('bg_color'),
                stroke_color=style.get('stroke_color'),
                stroke_width=style.get('stroke_width', 0),
                method='caption',
                size=(target_width, None)
            )

            # v2.x対応: with_start, with_duration, with_position
            txt = (txt.with_start(sub['start_offset'])
                   .with_duration(sub_duration)
                   .with_position(tuple(sub['position'])))
            sub_clips.append(txt)

        scene_video = CompositeVideoClip(sub_clips, size=(settings['width'], settings['height']))
        # v2.x対応: with_audio, with_duration
        scene_video = scene_video.with_audio(audio).with_duration(duration)

        scene_clips.append(scene_video)

    if not scene_clips:
        print("Error: 有効なシーンがありません。")
        return

    final_video = concatenate_videoclips(scene_clips, method="compose")

    if settings.get('bgm_path') and os.path.exists(settings['bgm_path']):
        bgm = AudioFileClip(settings['bgm_path']).with_volume_scaled(settings['bgm_volume'])
        bgm = bgm.with_duration(final_video.duration)

        from moviepy.audio.AudioClip import CompositeAudioClip
        combined_audio = CompositeAudioClip([final_video.audio, bgm])
        final_video = final_video.with_audio(combined_audio)

    output_path = settings.get('output_file', 'output_shorts.mp4')
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
        create_video_from_json(json_input)
    else:
        print("使い方: python manga_generator.py [設定JSONファイル名]")