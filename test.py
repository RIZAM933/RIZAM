from PIL import Image, ImageEnhance, ImageFilter
import pytesseract


def preprocess_image(image_path):
    image = Image.open(image_path).convert("L")  # Преобразование в градации серого
    image = image.filter(ImageFilter.SHARPEN)  # Применение фильтра резкости
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)  # Увеличение контраста
    return image

def extract_text(image):
    processed_image = preprocess_image(image)
    text = pytesseract.image_to_string(processed_image)
    return text


# Пример использования
text = extract_text('temp_image.png')
print(text)
