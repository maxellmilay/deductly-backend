from django.shortcuts import render
from django.http import HttpResponse
from .ocr import extract_text_from_image


def upload_receipt(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("receipt_image")
        if uploaded_file:
            try:
                # Call the OCR function from our module
                extracted_text = extract_text_from_image(uploaded_file)
            except Exception as e:
                return HttpResponse(f"Error processing image: {e}", status=400)
            return HttpResponse(f"Extracted Text: <pre>{extracted_text}</pre>")
        else:
            return HttpResponse("No file uploaded.", status=400)
    return render(request, "extract_text/upload.html")
