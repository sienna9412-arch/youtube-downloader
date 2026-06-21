# YouTube Info Viewer

유튜브 URL을 입력해 영상 정보를 조회하고 고화질로 다운로드하는 Windows 데스크톱 앱입니다.

## 주요 기능

- **영상 조회** — 제목, 조회수, 썸네일 표시
- **고화질 다운로드** — `bestvideo+bestaudio` 선택 후 ffmpeg로 mp4 병합
- **진행 표시줄** — 다운로드 진행률 실시간 표시
- **단독 실행** — Python 없이 `.exe` 파일 하나로 실행 가능

## 실행 방법

### 일반 사용자 (exe)

1. [Releases](../../releases) 페이지에서 `YouTubeInfoViewer.exe` 다운로드
2. 더블클릭으로 실행 (Python, ffmpeg, Node.js 설치 불필요)

### 개발자 (소스 실행)

```bash
# 패키지 설치
pip install -r requirements.txt

# 실행
python main.py
```

> ffmpeg와 Node.js가 시스템 PATH에 등록되어 있어야 합니다.

## 개발 환경

| 항목 | 버전 |
|------|------|
| Python | 3.14.6 |
| PyQt5 | 5.15.11 |
| yt-dlp | 2026.6.9 |
| requests | 2.34.2 |
| ffmpeg | 8.1.1 |

## exe 빌드

```bash
pip install pyinstaller pillow

# 아이콘 생성
python -c "
from PIL import Image, ImageDraw
sizes = [256,128,64,48,32,16]
images = []
for size in sizes:
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    r = size // 8
    draw.rounded_rectangle([0,0,size-1,size-1], radius=r, fill=(255,0,0,255))
    cx, cy = size//2, size//2
    tw, th = int(size*0.38), int(size*0.44)
    x0 = cx - tw//2 + int(size*0.04)
    draw.polygon([(x0,cy-th//2),(x0+tw,cy),(x0,cy+th//2)], fill=(255,255,255,255))
    images.append(img)
images[0].save('icon.ico', format='ICO', sizes=[(s,s) for s in sizes], append_images=images[1:])
"

# 빌드 (ffmpeg.exe, node.exe 경로를 실제 경로로 교체)
pyinstaller --onefile --windowed --name YouTubeInfoViewer \
  --icon icon.ico \
  --add-binary "path/to/ffmpeg.exe;." \
  --add-binary "path/to/node.exe;." \
  main.py
```

## 프로젝트 구조

```
.
├── main.py          # 메인 소스 코드
├── plan.md          # 프로젝트 계획서
├── requirements.txt # 패키지 의존성
├── icon.ico         # 앱 아이콘
└── .gitignore
```

## 라이선스

MIT
