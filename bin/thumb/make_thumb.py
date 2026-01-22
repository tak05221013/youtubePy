import sys
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def create_shorts_thumbnail(image_path, top_text, bottom_text, output_path):
    """
    YouTube Shorts風のサムネイルを作成する関数

    Args:
        image_path (str): メイン画像のパス
        top_text (str): 上部に表示するテキスト
        bottom_text (str): 下部に表示するテキスト
        output_path (str): 出力するファイルパス
    """

    # --- 設定項目 ---
    # 画像サイズ (Shorts標準: 1080x1920)
    CANVAS_WIDTH = 1080
    CANVAS_HEIGHT = 1920
    BG_COLOR = (255, 255, 255)  # 背景色：白

    # フォント設定 (環境に合わせてパスを変更してください)
    # Windowsの例: 'C:/Windows/Fonts/meiryo.ttc' (メイリオ) または 'msgothic.ttc'
    # Macの例: '/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc'
    FONT_PATH = "C:/Windows/Fonts/meiryob.ttc"

    # フォントが見つからない場合のフォールバック
    if not os.path.exists(FONT_PATH):
        # Windowsの一般的な代替フォント
        FONT_PATH = "C:/Windows/Fonts/msgothic.ttc"
        if not os.path.exists(FONT_PATH):
            print(f"エラー: フォントファイルが見つかりません。コード内の 'FONT_PATH' を修正してください。")
            return

    # フォントサイズ（文字数によって調整が必要な場合はここを変更）
    FONT_SIZE = 130

    # 色設定
    # 上部テキストの色（例：青系）
    TOP_TEXT_COLOR = (0, 100, 255)
    # 下部テキストの色（例：赤系）
    BOTTOM_TEXT_COLOR = (255, 0, 50)
    # 縁取りの色（白）
    STROKE_COLOR = (255, 255, 255)
    # 影の色（黒）
    SHADOW_COLOR = (0, 0, 0)

    # --- 処理開始 ---

    # 1. キャンバスの作成
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(canvas)

    # 2. 画像の読み込みと配置
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"画像の読み込みに失敗しました: {e}")
        return

    # 画像をキャンバスの幅に合わせてリサイズ（アスペクト比維持）
    aspect_ratio = img.height / img.width
    new_height = int(CANVAS_WIDTH * aspect_ratio)
    img_resized = img.resize((CANVAS_WIDTH, new_height), Image.Resampling.LANCZOS)

    # 画像をキャンバスの垂直中央に配置
    img_y = (CANVAS_HEIGHT - new_height) // 2
    canvas.paste(img_resized, (0, img_y))

    # 3. テキスト描画用のヘルパー関数
    def draw_styled_text(draw_obj, text, y_pos, font, fill_color):
        if not text:
            return

        # テキストのバウンディングボックスを取得して中央揃え位置を計算
        # getbbox returns (left, top, right, bottom)
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x_pos = (CANVAS_WIDTH - text_width) // 2

        # 縁取りの太さ
        stroke_width = 15

        # 影の描画（少しずらして黒で描画）
        shadow_offset = 10
        draw_obj.text((x_pos + shadow_offset, y_pos + shadow_offset), text, font=font, fill=SHADOW_COLOR)

        # 縁取り（白）の描画
        # stroke_widthパラメータを使って太い縁取りを描画
        draw_obj.text((x_pos, y_pos), text, font=font, fill=fill_color, stroke_width=stroke_width,
                      stroke_fill=STROKE_COLOR)

    # フォントのロード
    try:
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    except Exception as e:
        print(f"フォントのロードに失敗しました: {e}")
        return

    # 4. 上部テキストの描画
    # 改行が含まれている場合に対応
    top_lines = top_text.split('\\n')  # コマンドライン引数での改行文字対応
    current_y = 150  # 上部の開始位置

    for line in top_lines:
        # 上部は少し派手にするため、1行目をピンク、2行目を青にするなどのロジックも可能
        # ここではシンプルに指定色で描画
        draw_styled_text(draw, line, current_y, font, TOP_TEXT_COLOR)
        current_y += FONT_SIZE + 20  # 行間

    # 5. 下部テキストの描画
    bottom_lines = bottom_text.split('\\n')
    # 下部テキストの開始位置を計算（下から積み上げる）
    total_bottom_height = len(bottom_lines) * (FONT_SIZE + 20)
    current_y = CANVAS_HEIGHT - total_bottom_height - 250  # 下部の余白

    for line in bottom_lines:
        draw_styled_text(draw, line, current_y, font, BOTTOM_TEXT_COLOR)
        current_y += FONT_SIZE + 20

    # 6. 保存
    try:
        canvas.save(output_path)
        print(f"サムネイルを作成しました: {output_path}")
    except Exception as e:
        print(f"保存に失敗しました: {e}")


if __name__ == "__main__":
    # 引数チェック
    if len(sys.argv) < 5:
        print("使用法: python make_thumb.py [画像パス] [上部文字] [下部文字] [出力ファイル名]")
        print("例: python make_thumb.py input.jpg \"ボーイッシュだった\" \"最高すぎた\" output.png")
    else:
        input_img = sys.argv[1]
        top_txt = sys.argv[2]
        btm_txt = sys.argv[3]
        out_file = sys.argv[4]

        create_shorts_thumbnail(input_img, top_txt, btm_txt, out_file)