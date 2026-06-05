# 설치 및 실행

## requirements.txt

```
langgraph
langgraph-checkpoint-postgres>=2.0
langchain
langchain-google-genai
langchain-postgres
google-generativeai
fastapi
uvicorn[standard]
python-multipart
aiofiles
pymupdf
python-docx
libhwp
psycopg[binary]>=3.0
pgvector
pydantic
python-dotenv
```

## 환경 변수 (.env)

`.env.example` 복사 후 값 채우기:

```
GEMINI_API_KEY=
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
LAW_DATA_DIR=../data/laws
EVAL_SCORE_THRESHOLD=80
MAX_LOOP_COUNT=3
```

## 실행 방법

PostgreSQL이 실행 중이어야 한다. `DATABASE_URL`로 지정한 DB와 pgvector 확장이 미리 생성되어 있어야 한다:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

```bash
pip install -r requirements.txt
uvicorn src.main:app --reload
```

## 개발 도구

`requirements.txt`의 dev 섹션에 포함된 `ruff`(린터)와 `pytest`(테스트)는 앱 실행에는 불필요하지만 개발 시 사용한다:

```bash
ruff check src/ tests/
ruff format src/ tests/
pytest tests/
```
