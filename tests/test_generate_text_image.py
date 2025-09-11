from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

FONT_PATH = 'MiSans-Demibold.ttf'


def generate_text_image(text_lines, font_size=24, line_spacing=10, padding=20):
    """根据多行文本自动计算尺寸并生成图片"""
    # 加载字体，添加错误处理
    try:
        font = ImageFont.truetype(str(FONT_PATH), font_size)
    except OSError:
        font = ImageFont.load_default()
        print("警告: 无法加载指定字体，使用默认字体")

    # 计算每行文本的尺寸
    line_widths = []
    line_heights = []

    # 获取字体的基线信息
    ascent, descent = font.getmetrics()
    line_height = ascent + descent

    for line in text_lines:
        bbox = font.getbbox(line)
        width = bbox[2] - bbox[0]
        line_widths.append(width)
        line_heights.append(line_height)  # 使用统一的行高

    # 计算图片总尺寸
    max_width = max(line_widths) if line_widths else 0
    total_height = sum(line_heights) + line_spacing * (len(text_lines) - 1)

    img_width = max_width + padding * 2
    img_height = total_height + padding * 2

    # 创建图片
    image = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(image)

    # 绘制文本，从基线开始绘制
    y_offset = padding + ascent
    for i, line in enumerate(text_lines):
        draw.text((padding, y_offset - ascent), line, font=font, fill='black')
        y_offset += line_height + line_spacing

    return image


if __name__ == '__main__':
    # 测试多行文本
    test_lines = [
        "这是第一行测试文本",
        "This is the second line with English",
        "第三行包含中英文混合 Mixed Text",
        "最后一行文本"
    ]

    # 生成图片
    img = generate_text_image(test_lines, font_size=32, line_spacing=15, padding=30)

    # 保存并打开图片
    output_path = Path() / 'output_text_image.png'
    img.save(output_path)
    img.show()

    print(f"图片已生成并保存到: {output_path}")
    print(f"图片尺寸: {img.size}")