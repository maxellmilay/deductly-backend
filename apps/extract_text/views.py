from django.shortcuts import render
from django.http import HttpResponse
from .ocr import extract_text_from_image, generate_csv
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def upload_receipt(request):
    if request.method == "POST" and request.FILES.get("receipt_image"):
        image_file = request.FILES["receipt_image"]
        try:
            extracted_text, structured_data = extract_text_from_image(image_file)

            if not structured_data:
                return render(
                    request,
                    "extract_text/upload.html",
                    {
                        "error": "Could not extract any text from the image. Please try with a clearer image."
                    },
                )

            request.session["structured_data"] = structured_data
            return render(
                request,
                "extract_text/upload.html",
                {"extracted_text": extracted_text, "success": True},
            )
        except Exception as e:
            return render(request, "extract_text/upload.html", {"error": str(e)})
    return render(request, "extract_text/upload.html")


def download_csv(request):
    structured_data = request.session.get("structured_data", [])
    csv_content = generate_csv(structured_data)

    response = HttpResponse(csv_content, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="receipt_data.csv"'
    return response
