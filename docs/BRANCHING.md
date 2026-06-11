# GitHub 브랜치 관리 규칙 (potato / VoyageAI)

> 저장소 기본 브랜치: **`main`** (원격 `origin/main`)  
> 레포: `https://github.com/rlarlgns-evan/potato`  
> 작업 브랜치 접두어: **`vinnie`** (고정)

## 명명 규칙

| 자리 | 의미 | 예시 |
|------|------|------|
| `YYYY.MDD` | 릴리스·핫픽스 날짜 | `2026.611` (= 2026년 6월 11일) |
| `.0` / `.1` | 같은 날 릴리스(0) vs 핫픽스(1+) | `2026.611.0`, `2026.611.1` |
| `potato` | 이 프로젝트 코드명 (레포명) | `feature/potato/...` |
| `vinnie-ABC-00000` | 개인 작업 브랜치 (접두어 고정) | `vinnie-VOY-1234`, `vinnie-ABC-00000` |

개인 작업 브랜치: `{상위브랜치}/vinnie-{티켓}`  
예: `feature/potato/main/vinnie-VOY-1234`

## 브랜치 관계

```
main                          ← 프로덕션 (GitHub Pages 배포)
├── develop                   ← 통합 개발
│   ├── release/YYYY.MDD.0/main
│   │   └── release/YYYY.MDD.0/vinnie-ABC-00000
│   └── feature/potato/main
│        └── feature/potato/vinnie-ABC-00000
└── hotfix/YYYY.MDD.1/main
    └── hotfix/YYYY.MDD.1/vinnie-ABC-00000
```

### 현재 저장소 상태

| 브랜치 | 용도 |
|--------|------|
| `main` | Pages 배포·최신 기능 |
| `streamlit-backup` | Streamlit 앱 백업 (레거시, 위 트리 외) |

`develop` 및 `release/*`, `feature/*`, `hotfix/*` 는 필요 시 `main`에서 분기해 생성합니다.

## 브랜치 생성 예시

```bash
# develop 최초 생성 (한 번만)
git switch main
git pull origin main
git switch -c develop
git push -u origin develop

# 기능 메인 라인
git switch develop
git pull origin develop
git switch -c feature/potato/main

# 개인 작업 브랜치 (현재 브랜치 기준)
git switch -c feature/potato/vinnie-VOY-1234
```

## AI / Cursor 프롬프트

아래 문장을 채팅에 입력하면 에이전트가 **이 규칙**대로 git 명령을 실행합니다.

### 1. `00000 브랜치 생성해 줘`

- **현재 체크아웃된 브랜치**를 기준으로 `git switch -c` 실행
- 브랜치 이름: `{현재브랜치}/vinnie-{티켓}` — 티켓만 `00000`이면 `vinnie-ABC-00000` 형식
- 예: `feature/potato/main` 위에서 `VOY-1234` → `feature/potato/vinnie-VOY-1234`

### 2. `브랜치 최신화해줘`

1. **직계 상위 브랜치**로 이동 (예: `feature/potato/vinnie-VOY-1234` → `feature/potato/main`)
2. `git pull` 로 상위 브랜치 최신화
3. 작업 브랜치로 복귀
4. `git merge <상위브랜치>`
5. **충돌 시** merge 중단, 충돌 파일 목록만 알리고 사용자가 직접 해결

### 3. `브랜치 정리해 줘`

1. **직계 상위 브랜치**로 이동
2. `git branch -D <작업하던 브랜치>` 로 로컬 작업 브랜치 삭제
3. 상위 브랜치에서 `git pull` 로 최신화
4. 원격 브랜치 삭제는 사용자가 요청할 때만 `git push origin --delete ...`

## 상위 브랜치 매핑

| 현재 브랜치 패턴 | merge/pull 기준 상위 |
|------------------|----------------------|
| `feature/potato/vinnie-*` | `feature/potato/main` |
| `feature/potato/main` | `develop` |
| `release/YYYY.MDD.0/vinnie-*` | `release/YYYY.MDD.0/main` |
| `release/YYYY.MDD.0/main` | `develop` |
| `hotfix/YYYY.MDD.1/vinnie-*` | `hotfix/YYYY.MDD.1/main` |
| `hotfix/YYYY.MDD.1/main` | `main` |
| `develop` | `main` |

## 머지·배포

- **`main` → GitHub Pages** (`.github/workflows/pages.yml`)
- `develop` / `feature/*` 는 PR 또는 로컬 merge 후 상위로 올립니다.
- `hotfix/*` 는 `main`에 머지 후 필요 시 `develop`에도 back-merge.
