"""Generate the Rev-Eval logical architecture diagram (light + dark SVG).

Standard library only. Run from the repository root:

    python docs/diagrams/generate_diagrams.py

Writes docs/diagrams/rev-eval-architecture.svg and rev-eval-architecture-dark.svg.
Every box and arrow mirrors docker-compose.yml, nginx/nginx.conf, the API
gateway routing table and the service data stores; keep them in sync.
"""
import math
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent

THEMES = {
    "light": dict(bg="#ffffff", box="#f3f5fb", box2="#fafbff", group="#fafbff", group_stroke="#9aa3d9",
                  stroke="#3f4ab8", title="#14213d", text="#4b587c", accent="#3f4ab8",
                  green="#2e7d4f", green_fill="#eef7f1", amber="#9a6700", amber_fill="#fff8e6",
                  data_fill="#eef6fb", data="#0b6f8a", ops_fill="#f5f5f7", ops="#5b6170"),
    "dark": dict(bg="#0d1117", box="#161b22", box2="#11161d", group="#11161d", group_stroke="#4a5280",
                 stroke="#8b93e8", title="#e6edf3", text="#9aa4b2", accent="#8b93e8",
                 green="#56c88a", green_fill="#132a1d", amber="#e3b341", amber_fill="#2b2410",
                 data_fill="#0f2430", data="#4fb3cf", ops_fill="#161a20", ops="#9aa4b2"),
}

ALT = ("Rev-Eval logical architecture. Trainers and participants reach Nginx over HTTPS. Nginx terminates TLS, "
       "redirects HTTP to HTTPS, rate-limits the API path and adds security headers, then forwards page and BFF "
       "traffic to the Next.js frontend and /v1/api traffic to the API gateway. The Next.js BFF reads the JWT from "
       "an httpOnly cookie and calls the gateway with a Bearer token. Inside the private Docker network the gateway "
       "verifies the JWT and routes to user-service, test-management, reporting-and-analytics and "
       "question-management with identity headers and a request ID. User, test, session and score data live in "
       "PostgreSQL, which reporting reads with read-only queries; questions live in MongoDB and question images "
       "in MinIO. GitHub Actions CI runs lint, tests with a diff-coverage gate, Trivy scans and the frontend build.")


class Svg:
    def __init__(self, w, h, t, label):
        self.w, self.h, self.t, self.parts, self.label = w, h, t, [], label

    def rect(self, x, y, w, h, fill, stroke, dash=False, rx=12, sw=2):
        d = ' stroke-dasharray="7 6"' if dash else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                          f'stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def text(self, x, y, s, size=15, weight=400, color=None, anchor="middle"):
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                          f'fill="{color or self.t["text"]}" text-anchor="{anchor}">{escape(s)}</text>')

    def box(self, x, y, w, h, title, lines=(), title_color=None, fill=None, stroke=None):
        self.rect(x, y, w, h, fill or self.t["box"], stroke or self.t["stroke"])
        n = 1 + len(lines)
        top = y + h / 2 - (n - 1) * 11 + 6
        self.text(x + w / 2, top, title, 18, 700, title_color or self.t["title"])
        for i, ln in enumerate(lines):
            self.text(x + w / 2, top + 24 + i * 21, ln, 14.5)

    def zone(self, x, y, w, h, label, color=None, fill=None):
        self.rect(x, y, w, h, fill or self.t["group"], color or self.t["group_stroke"], dash=True, rx=18, sw=1.6)
        self.text(x + 22, y + 26, label, 14, 700, color or self.t["text"], "start")

    def line(self, pts, color=None):
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(pts))
        self.parts.append(f'<path d="{path}" fill="none" stroke="{color or self.t["accent"]}" stroke-width="2.5"/>')

    def arrow(self, pts, color=None, label=None, lx=None, ly=None, dash=False, anchor="middle"):
        # Explicit triangle arrowheads: SVG <marker> is not rendered by every viewer.
        c = color or self.t["accent"]
        d = ' stroke-dasharray="7 6"' if dash else ""
        (x1, y1), (x2, y2) = pts[-2], pts[-1]
        a = math.atan2(y2 - y1, x2 - x1)
        hl, hw = 13, 7
        bx, by = x2 - hl * math.cos(a), y2 - hl * math.sin(a)
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}"
                        for i, (x, y) in enumerate(list(pts[:-1]) + [(bx, by)]))
        self.parts.append(f'<path d="{path}" fill="none" stroke="{c}" stroke-width="2.5"{d}/>')
        p1 = (bx + hw * math.sin(a), by - hw * math.cos(a))
        p2 = (bx - hw * math.sin(a), by + hw * math.cos(a))
        self.parts.append(f'<path d="M{x2:.1f},{y2:.1f} L{p1[0]:.1f},{p1[1]:.1f} '
                          f'L{p2[0]:.1f},{p2[1]:.1f} z" fill="{c}"/>')
        if label:
            self.text(lx, ly, label, 13.5, 600, c, anchor)

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
                f'height="{self.h}" role="img" aria-label="{escape(self.label)}">\n'
                '<style>text{font-family:-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}</style>\n'
                f'<rect width="{self.w}" height="{self.h}" fill="{self.t["bg"]}"/>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


def architecture(t):
    W, H = 1400, 1150
    s = Svg(W, H, t, ALT)

    # 1. Public / external
    s.zone(40, 20, 1320, 130, "Public / external")
    s.box(500, 40, 400, 90, "Browser", ["trainer  ·  participant"], fill=t["box2"])

    # 2. Nginx edge
    s.zone(40, 180, 1320, 160, "Nginx edge", color=t["amber"], fill=t["amber_fill"])
    s.box(400, 210, 600, 108, "Nginx reverse proxy",
          ["TLS 1.2 / 1.3 termination  ·  HTTP → HTTPS redirect",
           "rate limit on /v1/api  ·  security headers"],
          title_color=t["amber"], fill=t["bg"], stroke=t["amber"])
    s.arrow([(700, 130), (700, 210)], label="HTTPS", lx=714, ly=176, anchor="start")

    # 3. Private Docker network
    s.zone(40, 370, 1320, 410, "Private Docker network  (application services, internal HTTP)")
    s.box(110, 430, 460, 112, "Next.js frontend + BFF",
          ["pages  ·  role-based routing", "httpOnly JWT cookie → Bearer header"], fill=t["box2"])
    s.box(830, 430, 460, 112, "API gateway",
          ["JWT verification  ·  path routing", "X-User-* identity  ·  X-Request-Id"],
          title_color=t["accent"], fill=t["box2"])
    s.arrow([(500, 318), (500, 430)], label="pages · /api (BFF)", lx=512, ly=414, anchor="start")
    s.arrow([(900, 318), (900, 430)], label="/v1/api/*", lx=912, ly=414, anchor="start")
    s.arrow([(570, 486), (830, 486)], label="REST · Bearer JWT", lx=700, ly=476)

    svc = [(60, "user-service", ["register · login", "issues JWT · bcrypt"]),
           (393, "test-management", ["tests · timed sessions · scoring", "row lock · idempotency key"]),
           (726, "reporting-and-analytics", ["reports · aggregates", "rankings · attempt history"]),
           (1060, "question-management", ["question bank", "presigned image URLs"])]
    sw, sy, bus_y = 280, 640, 595
    s.line([(1060, 542), (1060, bus_y)])
    s.line([(60 + sw / 2, bus_y), (1060 + sw / 2, bus_y)])
    s.text(700, bus_y - 12, "internal HTTP  ·  X-User-*  ·  X-Request-Id", 13.5, 600, t["accent"])
    for x, title, lines in svc:
        s.arrow([(x + sw / 2, bus_y), (x + sw / 2, sy)])
        s.box(x, sy, sw, 112, title, lines)

    # 4. Data layer
    s.zone(40, 810, 1320, 180, "Data layer", color=t["data"], fill=t["data_fill"])
    s.box(90, 860, 900, 104, "PostgreSQL",
          ["users · tests · sessions · submissions · scores",
           "shared database; reporting issues read-only queries (ADR 0001)"],
          title_color=t["data"], fill=t["bg"], stroke=t["data"])
    s.box(1030, 860, 150, 104, "MongoDB", ["questions"], title_color=t["data"], fill=t["bg"], stroke=t["data"])
    s.box(1200, 860, 140, 104, "MinIO", ["question", "images"], title_color=t["data"], fill=t["bg"], stroke=t["data"])
    s.arrow([(200, 752), (200, 860)], color=t["data"], label="SQL", lx=212, ly=800, anchor="start")
    s.arrow([(533, 752), (533, 860)], color=t["data"], label="SQL", lx=545, ly=800, anchor="start")
    s.arrow([(866, 752), (866, 860)], color=t["data"], dash=True, label="read-only SQL", lx=878, ly=800,
            anchor="start")
    s.arrow([(1105, 752), (1105, 860)], color=t["data"])
    s.arrow([(1270, 752), (1270, 860)], color=t["data"], label="S3 API", lx=1262, ly=800, anchor="end")

    # 5. Operations (cross-cutting)
    s.rect(40, 1020, 1320, 110, t["ops_fill"], t["ops"], rx=16, sw=1.6)
    s.text(70, 1052, "Operations  ·  cross-cutting", 14, 700, t["ops"], "start")
    s.text(700, 1080, "Docker Compose stack  ·  GitHub Actions CI: ruff · pytest + 80 % diff coverage · "
           "Postgres / MongoDB integration tests", 14.5, 400, t["title"])
    s.text(700, 1106, "Trivy scan per service  ·  ESLint (zero warnings) · Next.js build · Vitest · "
           "build-provenance attestation  ·  Playwright E2E on demand", 14.5, 400, t["title"])
    return s.render()


if __name__ == "__main__":
    for theme, palette in THEMES.items():
        suffix = "" if theme == "light" else "-dark"
        (OUT / f"rev-eval-architecture{suffix}.svg").write_text(architecture(palette), encoding="utf8", newline="\n")
    print(f"written to {OUT}")
