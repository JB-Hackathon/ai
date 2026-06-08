from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class ReviewState(TypedDict):
    # 사용자 입력
    content_text: str  # 사용자가 직접 입력한 원본 텍스트 (광고 문구, 제품 설명 등)
    content_file_path: list[str]  # 업로드된 파일의 임시 저장 경로 목록 (이미지·PDF·DOCX·HWP)
    channel_type: str  # 광고 채널 (홈페이지·SNS·문자·카카오톡·기타)
    content_category: str  # 콘텐츠 유형 (금융상품 광고·업무광고·정보제공·기타)
    product_category: str | None  # 금융상품 범주 (예금성·대출성·카드·투자성 등; 광고일 때만 지정)
    business_sector: str  # 금융 업종 (은행·여신금융·금융투자·저축은행·기타)
    language_code: str  # 콘텐츠 언어 ISO 코드 (ko 한국어·en 영어·fil 필리핀어·km 캄보디아어·zh 중국어·vi 베트남어)

    # 실행 중 채워지는 필드
    ocr_text: str  # ocr_node가 파일에서 추출한 텍스트; 여러 파일은 "\n\n"으로 구분
    original_content_text: str  # translation_node가 번역 전 content_text를 백업
    original_ocr_text: str  # translation_node가 번역 전 ocr_text를 백업
    law_list: list[str]  # rag_node가 검색한 관련 법령 조항 목록 ("[법령명] (발령기관)\n내용" 포맷)
    checklist: list[str]  # checklist_node가 생성한 심의 기준 항목; 재심의 루프 중에도 고정
    conditional_checklist: list[str]  # checklist_node가 생성한 조건부 참고 항목 (직접 미적용 기준)
    needs_visual_review: bool  # 이미지·스캔 PDF 포함 시 True; review_node가 VLM으로 처리
    review_result: str  # review_node가 작성한 심의 결과 보고서
    eval_score: float  # evaluator_node의 평가 점수 (0~100; 80 이상이면 합격)
    eval_feedback: str  # evaluator_node의 개선 지시; 재심의 시 review_node 프롬프트에 포함
    loop_count: int  # 심의 루프 누적 횟수 (evaluator_node가 매번 +1; 3회 도달 시 강제 종료)
    review_passed: bool  # 최종 합격 여부 (eval_score >= 80이면 True)
    messages: Annotated[list, add_messages]  # LangGraph 워크플로우 대화 로그 (현재 미사용)
