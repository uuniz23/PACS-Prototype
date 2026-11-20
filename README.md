# PACS-Prototype

Python · Streamlit · Firebase(Authentication, Cloud Firestore) 기반 교육용 웹 PACS 프로토타입입니다.
(초급프로젝트 PBL Term Project)

> **팀 공통 Python 버전: `3.__`** ← 팀장이 정해 이 줄을 채웁니다. `python --version`의 앞 두 자리가 같아야 합니다.

## 프로젝트 구조

```
PACS-Prototype/
├── streamlit_app.py          앱 진입점 (streamlit run 대상)
├── app/
│   ├── components/sidebar.py 사이드바
│   ├── pages/                화면 (현재는 샘플 화면)
│   ├── utils/helpers.py      세션 상태 도우미
│   └── logic.py              계산 로직 (테스트 대상)
├── tests/test_logic.py       pytest 테스트
├── .streamlit/
│   ├── config.toml           테마·서버 설정
│   └── secrets.toml.example  키 이름 예시 (값 없음)
├── .github/
│   ├── workflows/ci.yml      PR마다 pytest 자동 실행
│   └── pull_request_template.md
├── requirements.txt          앱 패키지
└── requirements-dev.txt      테스트 패키지 (pytest)
```

샘플 화면과 샘플 데이터는 PACS 기능으로 교체될 예정입니다. 폴더 구조는 설계 문서에서 확정합니다.

## 로컬 실행

```bash
git clone https://github.com/uuniz23/PACS-Prototype.git
cd PACS-Prototype

python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt

streamlit run streamlit_app.py   # http://localhost:8501
pytest                            # 테스트
```

줄 맨 앞에 `(.venv)`가 보이는 상태(가상환경이 켜진 상태)에서 실행합니다.

## Firebase 설정 (비밀 값)

- 실제 키 값은 이 저장소에 없습니다. 값은 **팀장에게 직접 받아** `.streamlit/secrets.toml`에 저장합니다.
- 필요한 키 이름은 `.streamlit/secrets.toml.example`을 참고합니다.
- `secrets.toml`, 서비스 계정 JSON, 비밀번호는 커밋·Issue·PR·단체방에 올리지 않습니다.

## 협업 규칙

1. 작업은 담당자가 지정된 **Issue**에서 시작합니다.
2. `main`을 최신으로 받고(`git pull origin main`) Issue별 **새 브랜치**에서 작업합니다. 예: `feat/case-register`, `fix/roi-range-check`
3. PR 전에 로컬 `pytest`를 통과시키고, 앱을 실행해 내 기능을 직접 확인합니다.
4. **Pull Request**를 올립니다. 양식을 채우고 리뷰어를 지정합니다. `main`에는 직접 push하지 않습니다.
5. PR 하단 Checks의 CI(pytest)가 초록색인지 확인하고, 리뷰어 승인 후 병합합니다.

CI(GitHub Actions)는 **pytest만** 실행합니다. 배포와 비밀 값 사용은 하지 않습니다.

## 배포 (JCloud)

> 배포 방법이 확인되면 이 항목에 실행·배포·복구 순서를 적습니다.

## 사용한 AI·수업 코드·외부 자료

> 사용 부분 / 도구·출처 / 직접 수정·검증한 내용을 표로 정리해 추가합니다.
