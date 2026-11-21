# PACS-Prototype

Python · Streamlit · Firebase(Authentication, Cloud Firestore) 기반 교육용 웹 PACS 프로토타입입니다.
(초급프로젝트 PBL Term Project)

> **팀 공통 Python 버전: `3.14`** `python --version`의 앞 두 자리가 같아야 합니다.

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
# Windows Git Bash:   source .venv/Scripts/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Windows cmd:        .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate

pip install -r requirements.txt -r requirements-dev.txt

streamlit run streamlit_app.py   # http://localhost:8501
pytest                            # 테스트
```

줄 맨 앞에 `(.venv)`가 보이는 상태(가상환경이 켜진 상태)에서 실행합니다.
Windows는 가상환경 폴더가 `bin`이 아니라 `Scripts`입니다. 사용하는 터미널(Git Bash, PowerShell, cmd)에 맞는 명령을 고르세요.

### 자주 막히는 곳

| 증상 | 원인 | 해결 |
|---|---|---|
| `streamlit: command not found`, `pytest: command not found` | 가상환경이 켜져 있지 않음 (패키지가 가상환경 밖에 설치됨) | 위 활성화 명령 실행 → `(.venv)` 확인 → `pip install -r requirements.txt -r requirements-dev.txt` 다시 실행 |
| `source: .venv/bin/activate: No such file or directory` (Windows) | Windows는 `bin`이 아니라 `Scripts` | `source .venv/Scripts/activate` |
| PowerShell에서 `Activate.ps1` 실행이 막힘 | 스크립트 실행 정책 | cmd에서 `.venv\Scripts\activate.bat` 사용 |
| `python`을 찾을 수 없음 (Windows) | python 경로 미등록 | `py -3.11 -m venv .venv`처럼 `py` 런처 사용 (버전은 팀 공통 버전) |
| `Port 8501 is already in use` | 이전에 켠 앱이 실행 중 | 이전 터미널에서 `Ctrl + C`, 또는 `streamlit run streamlit_app.py --server.port 8502` |

임시로 PATH 문제만 피하려면 `python -m streamlit run streamlit_app.py`, `python -m pytest`처럼 실행할 수 있습니다. 평소에는 가상환경을 켠 상태로 사용합니다.

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

서버: JCloud 인스턴스 1대(Ubuntu, micro: vCPU 2 / RAM 2 GiB / 디스크 10 GiB). 서버 접속과 배포 반영은 **팀장만** 합니다. 팀원은 아래 주소에서 확인만 합니다.

- 접속 주소: `http://s.jedutools.io:53128` (서버 내부 포트 8080 → 공인 포트 53128으로 포워딩)
- 서버 접속: SSH (`s.jedutools.io`, 포트 `13128`, 계정 `ubuntu`, 키 파일 인증). 키 파일은 팀장만 보관하며 저장소에 올리지 않습니다.
- 앱 위치: 서버의 `~/PACS-Prototype` (가상환경 `.venv`, 서버에는 `requirements.txt`만 설치)
- 비밀 값: 서버에서 직접 만든 `.streamlit/secrets.toml` 사용 (git에 없으며, 값을 바꾸면 서버에서 직접 수정 후 앱 재시작)

### 앱 실행 (tmux로 상시 실행)

```bash
tmux new -s app                      # 처음 한 번 세션 만들기
cd ~/PACS-Prototype && source .venv/bin/activate
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0
# Ctrl+B 누르고 손을 뗀 뒤 소문자 d → 세션에서 빠져나와도 앱은 계속 실행
```

- 세션 목록: `tmux ls` / 다시 들어가기: `tmux attach -t app`
- 서버가 재부팅되면 앱이 꺼지므로 위 순서로 다시 실행합니다.

### 배포 반영 (PR 병합 후, 팀장이 서버에서)

```bash
tmux attach -t app                   # Ctrl+C로 앱 중지
git pull origin main
pip install -r requirements.txt      # 패키지가 바뀐 경우만
streamlit run streamlit_app.py --server.port 8080 --server.address 0.0.0.0
# Ctrl+B, d
```

- 서버에서는 `main`만 받고, **서버 코드는 직접 수정하지 않습니다**(수정은 항상 PR).
- 반영 후 팀 채널에 "배포 반영함"을 알립니다.
- 앱이 응답하지 않으면 `tmux attach -t app`으로 들어가 오류 메시지를 확인하고 재시작합니다.

## 사용한 AI·수업 코드·외부 자료

> 사용 부분 / 도구·출처 / 직접 수정·검증한 내용을 표로 정리해 추가합니다.
