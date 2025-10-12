import pytest
from unittest.mock import MagicMock, patch
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Use a font path relative to this test file
FONT_PATH = Path(__file__).parent / 'MiSans-Demibold.ttf'


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


@patch("test_generate_text_image.ImageFont.truetype")
@patch("test_generate_text_image.Image.new")
@patch("test_generate_text_image.ImageDraw.Draw")
def test_generate_text_image_logic(mock_draw, mock_new_image, mock_truetype):
    # Arrange
    # Mock font metrics
    mock_font = MagicMock()
    mock_font.getmetrics.return_value = (18, 2)  # ascent, descent
    mock_font.getbbox.side_effect = lambda text: {
        "hello": (0, 0, 40, 20),
        "world": (0, 0, 50, 20),
    }[text]
    mock_truetype.return_value = mock_font

    # Mock Image and Draw objects
    mock_image_instance = MagicMock()
    mock_new_image.return_value = mock_image_instance
    mock_draw_instance = MagicMock()
    mock_draw.return_value = mock_draw_instance

    text_lines = ["hello", "world"]
    font_size = 16
    line_spacing = 5
    padding = 10

    # Act
    generate_text_image(text_lines, font_size, line_spacing, padding)

    # Assert
    # Verify font loading
    mock_truetype.assert_called_with(str(FONT_PATH), font_size)

    # Verify image creation with correct dimensions
    # max_width = 50, total_height = 20 + 20 + 5 = 45
    # img_width = 50 + 10*2 = 70
    # img_height = 45 + 10*2 = 65
    mock_new_image.assert_called_with('RGB', (70, 65), 'white')

    # Verify drawing calls
    assert mock_draw_instance.text.call_count == 2
    # First call: y_offset = padding + ascent = 10 + 18 = 28
    # draw.text((10, 28 - 18), "hello", ...) -> (10, 10)
    mock_draw_instance.text.assert_any_call((10, 10), "hello", font=mock_font, fill='black')
    # Second call: y_offset += line_height + line_spacing = 28 + 20 + 5 = 53
    # draw.text((10, 53 - 18), "world", ...) -> (10, 35)
    mock_draw_instance.text.assert_any_call((10, 35), "world", font=mock_font, fill='black')


# Minimal sanity test for the helper
def test_generate_text_image_basic():
    img = generate_text_image(["hello", "world"], font_size=16, line_spacing=6, padding=8)
    assert isinstance(img, Image.Image)
    w, h = img.size
    assert w > 0 and h > 0


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
    output_path = Path(__file__).parent / 'output_text_image.png'
    img.save(output_path)
    img.show()

    print(f"图片已生成并保存到: {output_path}")
    print(f"图片尺寸: {img.size}")