# OCR 노드

## 역할

입력 파일에서 텍스트를 추출한다. 추출된 텍스트(`ocr_text`)는 이후 RAG 노드와 심의 노드의 입력으로 결합된다.

## 파일 타입별 처리

| 파일 타입 | 라이브러리 | 처리 방식 |
|-----------|-----------|-----------|
| PDF (디지털) | `PyMuPDF (fitz)` | 첫 페이지 50자 이상 → `page.get_text()` 고속 추출 |
| PDF (스캔) | `gemini-2.5-flash` | 첫 페이지 텍스트 부족 → Gemini Vision API fallback |
| DOCX | `python-docx` | `Document.paragraphs` 순회 |
| 이미지 (jpg/png) | `gemini-2.5-flash` | Gemini Vision API |
| HWP | `libhwp` | HWP 파싱 |

## 구현 구조

파일 타입 판별은 순수 결정론적 연산이므로 LLM tool call 없이 코드에서 직접 처리한다.
`ocr_node` 단일 노드가 확장자를 보고 적절한 핸들러 함수로 디스패치한다.
각 핸들러는 별도 모듈로 분리하여 코드 길이 문제를 해결한다.

```
src/nodes/ocr/
├── __init__.py   # ocr_node 함수 정의 및 export
├── pdf.py        # extract_pdf() — PyMuPDF + Gemini Vision fallback
├── docx.py       # extract_docx() — python-docx
├── hwp.py        # extract_hwp() — libhwp
└── image.py      # extract_image() — Gemini Vision
```

```python
# __init__.py 핵심 로직
HANDLERS = {
    ".pdf":  extract_pdf,
    ".docx": extract_docx,
    ".hwp":  extract_hwp,
    ".jpg":  extract_image,
    ".png":  extract_image,
}

def ocr_node(state):
    if not state.get("input_files"):
        return {}  # 파일 없으면 통과 (별도 분기 노드 불필요)
    texts = []
    is_visual = False
    for path in state["input_files"]:
        ext = Path(path).suffix.lower()
        result = HANDLERS[ext](path)
        if isinstance(result, tuple):
            # extract_pdf()가 스캔 감지 시 (text, True) 반환
            texts.append(result[0])
            is_visual = is_visual or result[1]
        else:
            texts.append(result)
            if ext in (".jpg", ".png"):
                is_visual = True
    return {"ocr_text": "\n\n".join(texts), "needs_visual_review": is_visual}
```

`extract_pdf()`는 스캔 감지 시 `(text: str, is_visual: bool)` 튜플을 반환한다. 디지털 PDF는 `(text, False)` 반환. 이미지 파일(`.jpg`, `.png`)은 항상 `needs_visual_review = True`로 처리한다.
