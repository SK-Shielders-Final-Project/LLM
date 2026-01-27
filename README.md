<<<<<<< HEAD
🛡️ LLM-SecLab: Implementation & Penetration Testing
이 리포지토리는 거대언어모델(LLM)의 직접적인 구현과 해당 모델 및 애플리케이션에 대한 **보안 취약점 진단(모의해킹)**을 연구하기 위한 프로젝트입니다. LLM 아키텍처의 이해를 바탕으로, 실제 발생 가능한 공격 벡터를 식별하고 대응 방안을 제시합니다.

## 프로젝트 구조
```
app/
  api/                 # FastAPI 라우터
  core/                # 설정/로깅
  services/            # LLM, AWS 데이터 접근, 프롬프트 생성
  main.py              # FastAPI 엔트리
  app.py               # 로컬 테스트용 CLI
  schemas.py           # 요청/응답 스키마
```

## 주요 엔드포인트
- `POST /api/v1/summary/price`
- `POST /api/v1/summary/usage`
- `POST /api/v1/assistant`
- `GET /health`

## 환경 변수 (선택)
- `MODEL_ID` (기본: `yanolja/YanoljaNEXT-EEVE-10.8B`)
- `SANDBOX_MODE` (기본: `true`)  
- `USE_MOCK_LLM` (기본: `true`)
- `USE_MOCK_DATA` (기본: `true`)
- `AWS_REGION`, `PRICING_TABLE`, `USAGE_TABLE`

=======
[Model Info]
https://huggingface.co/yanolja/YanoljaNEXT-EEVE-10.8B?local-app=vllm
<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/2058c7f1-5f6d-4224-818d-b3da2fc1308e" />
>>>>>>> d9f51d9c4fb07d61727eadd198a8ca30bc627b9d


<img width="1024" height="559" alt="image" src="https://github.com/user-attachments/assets/e3e1f798-aef1-4bb5-9aaf-652d76b62ee0" />

<img width="2816" height="1536" alt="Generated_image" src="https://github.com/user-attachments/assets/8853c1f5-c278-45ea-bd87-3ea26dccdbe7" />


