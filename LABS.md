# Tài Liệu Chi Tiết Bài Lab Nâng Cao — Giám Sát & Canary Deployment

---

## Mục Lục

1. [Giải thích các khái niệm nâng cao](#1-giải-thích-các-khái-niệm-nâng-cao)
2. [Cấu trúc thư mục mở rộng](#2-cấu-trúc-thư-mục-mở-rộng)
3. [Giải thích chi tiết từng file mới](#3-giải-thích-chi-tiết-từng-file-mới)
4. [Luồng hoạt động tổng thể — Giám sát & Canary](#4-luồng-hoạt-động-tổng-thể--giám-sát--canary)
5. [Chi tiết từng bài Lab và các bước thực hiện](#5-chi-tiết-từng-bài-lab-và-các-bước-thực-hiện)
   - [Lab 1: Cài đặt Prometheus Stack & Argo Rollouts qua GitOps](#lab-1-cài-đặt-prometheus-stack--argo-rollouts-qua-gitops)
   - [Lab 2: Xây dựng và Docker hóa Flask API có Metrics](#lab-2-xây-dựng-và-docker-hóa-flask-api-có-metrics)
   - [Lab 3: Triển khai Canary Rollout & Cấu hình ServiceMonitor](#lab-3-triển-khai-canary-rollout--cấu-hình-servicemonitor)
   - [Lab 4: Thực hiện Canary Deployment & Giám sát trực quan](#lab-4-thực-hiện-canary-deployment--giám-sát-trực-quan)
6. [Phụ lục: Xử lý lỗi phổ biến](#6-phụ-lục-xử-lý-lỗi-phổ-biến)

---

## 1. Giải Thích Các Khái Niệm Nâng Cao

Trước khi bắt tay vào thực hành, hãy hiểu rõ các thuật ngữ quan trọng sẽ sử dụng xuyên suốt 4 bài Lab:

### Prometheus & Grafana là gì?

**Prometheus** là hệ thống giám sát và cảnh báo mã nguồn mở. Nó hoạt động theo cơ chế **Pull** — tức là định kỳ đi "quét" (scrape) các endpoint `/metrics` của ứng dụng để thu thập các thông số như số lượng request, thời gian xử lý, số lỗi 500...

**Grafana** là công cụ trực quan hóa dữ liệu. Nó kết nối tới Prometheus để vẽ các biểu đồ đẹp mắt (Dashboard), giúp bạn theo dõi sức khỏe hệ thống trực quan hơn.

> **Ví dụ thực tế**: Prometheus giống như một **bác sĩ khám định kỳ** — cứ mỗi 15 giây, bác sĩ lại đến "khám" ứng dụng của bạn để đo các chỉ số (nhịp tim = số request, huyết áp = tỷ lệ lỗi). Grafana thì giống như **bảng theo dõi sức khỏe trực quan** ở phòng bệnh, vẽ biểu đồ lên màn hình để bạn dễ quan sát.

### ServiceMonitor là gì?

Thông thường, để Prometheus biết cần thu thập metric từ service nào, bạn phải cấu hình thủ công trong file Prometheus config. Rất bất tiện!

Trong Kubernetes sử dụng **Prometheus Operator**, bạn chỉ cần tạo một tài nguyên gọi là **ServiceMonitor**. Prometheus Operator sẽ tự động phát hiện ServiceMonitor này và bảo Prometheus đi scrape Service tương ứng.

> **Ví dụ thực tế**: ServiceMonitor giống như **tấm bảng tên bệnh nhân** treo ở đầu giường trong bệnh viện. Khi bạn tạo bảng tên mới, bác sĩ (Prometheus) tự động biết có bệnh nhân mới cần khám — bạn không cần phải đi tìm bác sĩ và dặn dò từng người.

### PrometheusRule & AlertManager là gì?

- **PrometheusRule** là tài nguyên Kubernetes cho phép bạn định nghĩa các quy tắc cảnh báo (alert rules). Ví dụ: "Nếu tỷ lệ lỗi HTTP 5xx vượt quá 5% trong vòng 10 giây → kích hoạt cảnh báo".
- **AlertManager** nhận các cảnh báo từ Prometheus và xử lý chúng: gom nhóm, lọc trùng lặp, và gửi thông báo qua email, Slack, PagerDuty...

> **Ví dụ thực tế**: PrometheusRule giống như **ngưỡng cảnh báo trên máy đo** (ví dụ: nhịp tim > 120 thì báo động). AlertManager giống như **y tá trực** — khi máy báo động kêu, y tá sẽ gom thông tin lại và gọi điện báo cho bác sĩ trưởng (gửi email).

### Argo Rollouts là gì?

Deployment mặc định của Kubernetes chỉ hỗ trợ chiến lược cập nhật **RollingUpdate** — thay thế dần pod cũ bằng pod mới. Chiến lược này khá rủi ro vì nếu pod mới có lỗi logic ẩn, hệ thống vẫn sẽ thay thế 100% pod cũ trước khi bạn kịp phát hiện.

**Argo Rollouts** là một Kubernetes Controller cung cấp các chiến lược triển khai nâng cao:
- **Blue-Green**: Triển khai 2 bộ pod hoàn toàn, chuyển traffic một lần từ "blue" (cũ) sang "green" (mới).
- **Canary**: Chuyển traffic từ từ theo tỷ lệ phần trăm (25% → 50% → 100%).

> **Ví dụ thực tế**: Deployment mặc định giống như **đổi toàn bộ đầu bếp trong nhà hàng cùng lúc** — nếu đầu bếp mới nấu dở, tất cả khách đều bị ảnh hưởng. Argo Rollouts giống như **cho đầu bếp mới thử phục vụ 25% bàn trước** — nếu khách phàn nàn, bạn rút lại ngay mà 75% bàn còn lại không hề hay biết.

### Chiến lược Canary là gì?

Canary là chiến lược phát hành phiên bản mới (`v2`) bằng cách chuyển một **tỷ lệ phần trăm nhỏ lưu lượng truy cập** (ví dụ 25%) sang phiên bản mới, trong khi phần lớn người dùng vẫn dùng bản cũ (`v1`).

Sau một thời gian kiểm tra (qua Prometheus hoặc kiểm tra thủ công), nếu phiên bản mới hoạt động tốt, bạn sẽ tăng tỷ lệ lên 50%, 100% để hoàn tất phát hành. Nếu phát hiện lỗi, bạn có thể **Rollback ngay lập tức** mà không ảnh hưởng tới 75% người dùng còn lại.

### AnalysisTemplate & AnalysisRun là gì?

- **AnalysisTemplate** là "khuôn mẫu đánh giá" — nó mô tả cách đo lường chất lượng phiên bản mới (truy vấn Prometheus, điều kiện thành công/thất bại).
- **AnalysisRun** là "phiên đánh giá thực tế" — được Argo Rollouts tự động tạo ra dựa trên AnalysisTemplate mỗi khi có Canary deployment. Nó chạy truy vấn Prometheus định kỳ và đưa ra kết luận: `Successful` (đạt) hoặc `Failed` (không đạt → tự động rollback).

> **Ví dụ thực tế**: AnalysisTemplate giống như **đề thi** (câu hỏi + điểm chuẩn đậu). AnalysisRun giống như **bài thi thực tế** — khi có "thí sinh" (phiên bản mới), đề thi được phát ra, nếu điểm thi dưới chuẩn → trượt (rollback).

---

## 2. Cấu Trúc Thư Mục Mở Rộng

Dưới đây là cấu trúc thư mục của dự án **sau khi hoàn thành cả 4 bài Lab**, so sánh với cấu trúc ban đầu trong `README.md`:

```
gitops/                              ← Thư mục gốc của kho lưu trữ Git
│
├── README.md                        ← Tài liệu dự án cơ bản (App-of-Apps)
├── LABS.md                          ← Tài liệu bạn đang đọc (4 bài Lab nâng cao)
│
├── .github/workflows/
│   └── validate.yml                 ← CI Pipeline (giữ nguyên từ dự án ban đầu)
│
├── app/                             ← [MỚI] MÃ NGUỒN ỨNG DỤNG FLASK API
│   ├── app.py                       ← Flask API: xuất metrics, giả lập lỗi
│   └── Dockerfile                   ← Đóng gói API thành Docker image
│
├── argocd/                          ← CẤU HÌNH ARGO CD
│   ├── root.yaml                    ← Ứng dụng gốc (giữ nguyên)
│   └── apps/
│       ├── web.yaml                 ← App con: web (giữ nguyên)
│       ├── frontend.yaml            ← App con: frontend (giữ nguyên)
│       ├── backend.yaml             ← App con: backend (giữ nguyên)
│       ├── kube-prometheus-stack.yaml   ← [MỚI - Lab 1] App con: Prometheus + Grafana
│       ├── argo-rollouts.yaml       ← [MỚI - Lab 1] App con: Argo Rollouts Controller
│       └── api.yaml                 ← [MỚI - Lab 3] App con: Flask API Rollout
│
├── k8s/                             ← TÀI NGUYÊN K8S CŨ (giữ nguyên)
│   ├── web/
│   ├── frontend/
│   └── backend/
│
└── k8s-api/                         ← [MỚI - Lab 3] TÀI NGUYÊN K8S CHO FLASK API
    ├── api.yaml                     ← Rollout (thay thế Deployment) + Service
    ├── servicemonitor.yaml          ← ServiceMonitor: Prometheus scrape API metrics
    ├── analysistemplate.yaml         ← AnalysisTemplate: đo lường tỷ lệ thành công
    └── prometheusrule.yaml          ← PrometheusRule: cảnh báo khi lỗi > 5%
```

### Tại sao tách thành thư mục `k8s-api/` riêng?

| Thư mục | Loại tài nguyên | Lý do tách |
| :--- | :--- | :--- |
| `k8s/` | Deployment, ConfigMap, Service chuẩn | Tài nguyên Kubernetes **mặc định**, `kubeconform` có thể validate |
| `k8s-api/` | **Rollout** (CRD), AnalysisTemplate, ServiceMonitor, PrometheusRule | Tài nguyên **CRD tùy chỉnh** — `kubeconform` mặc định không nhận diện schema của chúng, sẽ báo lỗi nếu đặt chung |

> Nói cách khác: `k8s/` chứa "đồ chuẩn Kubernetes", `k8s-api/` chứa "đồ mở rộng" dùng CRD từ Argo Rollouts và Prometheus Operator. Tách ra giúp CI Pipeline (`validate.yml`) không bị lỗi khi kiểm tra cú pháp.

---

## 3. Giải Thích Chi Tiết Từng File Mới

### 3.1. `argocd/apps/kube-prometheus-stack.yaml` — Cài đặt Prometheus, Grafana & AlertManager

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kube-prometheus-stack       # Tên hiển thị trên Argo CD UI
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "1"  # Cài đặt SAU khi namespace đã sẵn sàng
spec:
  project: default
  source:
    chart: kube-prometheus-stack     # ⭐ Đây là Helm Chart, KHÔNG phải thư mục Git
    repoURL: https://prometheus-community.github.io/helm-charts  # Kho Helm Charts
    targetRevision: 65.1.1           # Phiên bản cố định của Helm Chart
    helm:
      values: |
        crds:
          enabled: false             # ⭐ Tắt tự động cài CRD (ta cài thủ công trước)
        grafana:
          adminPassword: admin       # Mật khẩu đăng nhập Grafana mặc định
        prometheus:
          prometheusSpec:
            # ⭐ RẤT QUAN TRỌNG: Cho phép Prometheus thu thập metric từ MỌI
            # ServiceMonitor trong cluster, không bắt buộc phải trùng label
            # với Helm release. Nếu không có dòng này, ServiceMonitor của
            # API sẽ bị Prometheus "phớt lờ" hoàn toàn.
            serviceMonitorSelectorNilUsesHelmValues: false
        alertmanager:
          config:
            global:
              smtp_smarthost: 'smtp.gmail.com:587'    # Máy chủ SMTP của Gmail
              smtp_from: 'alertmanager@example.com'    # Địa chỉ gửi
              smtp_require_tls: true                   # Bắt buộc mã hóa TLS
            route:
              group_by: ['alertname']   # Gom các alert cùng tên thành 1 nhóm
              group_wait: 5s            # Chờ 5s để gom alert trước khi gửi
              group_interval: 10s       # Khoảng cách giữa 2 lần gửi nhóm
              repeat_interval: 5m       # Gửi lặp lại mỗi 5 phút nếu alert chưa hết
              receiver: 'email-notifications'  # Receiver mặc định
            receivers:
            - name: 'null'              # Receiver "rỗng" — dùng để bỏ qua alert không cần
            - name: 'email-notifications'
              email_configs:
              - to: 'ddor2812@gmail.com'    # ⭐ Địa chỉ email nhận cảnh báo
                send_resolved: true          # Gửi thông báo khi alert đã được giải quyết
  destination:
    server: https://kubernetes.default.svc
    namespace: monitoring            # Tất cả Pod Prometheus/Grafana sẽ chạy ở đây
  syncPolicy:
    automated:
      prune: false                   # KHÔNG xóa tài nguyên cũ (an toàn hơn cho hệ thống giám sát)
      selfHeal: true
    syncOptions:
    - CreateNamespace=true           # Tự tạo namespace "monitoring" nếu chưa có
    - ServerSideApply=true           # ⭐ Bắt buộc! Giải quyết lỗi CRD quá lớn (> 256KB)
```

**Giải thích bằng ngôn ngữ đời thường:**

File này nói với Argo CD rằng: "Hãy cài đặt bộ công cụ giám sát Prometheus + Grafana + AlertManager từ Helm Chart, đặt chúng vào namespace `monitoring`. Khi có cảnh báo nghiêm trọng, gửi email tới `ddor2812@gmail.com`."

**Điểm đặc biệt**: Đây là ứng dụng Argo CD duy nhất sử dụng **Helm Chart** thay vì thư mục Git. Argo CD hỗ trợ cả hai nguồn: Git repository và Helm repository.

---

### 3.2. `argocd/apps/argo-rollouts.yaml` — Cài đặt Argo Rollouts Controller

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argo-rollouts
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  project: default
  source:
    chart: argo-rollouts              # Helm Chart cho Argo Rollouts
    repoURL: https://argoproj.github.io/argo-helm  # Kho Helm Charts của ArgoProj
    targetRevision: 2.37.7            # Phiên bản Helm Chart
  destination:
    server: https://kubernetes.default.svc
    namespace: argo-rollouts          # Namespace riêng cho Rollouts Controller
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

**Giải thích bằng ngôn ngữ đời thường:**

File này cài đặt **Argo Rollouts Controller** — một "bộ não" chạy ngầm trong cluster, chuyên theo dõi và điều khiển các tài nguyên loại `Rollout`. Không có controller này, Kubernetes sẽ không hiểu loại tài nguyên `Rollout` và báo lỗi.

> Tương tự như bạn cần cài Argo CD trước rồi mới dùng được `Application`, bạn cần cài Argo Rollouts trước rồi mới dùng được `Rollout`.

---

### 3.3. `argocd/apps/api.yaml` — Khai báo ứng dụng Flask API

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: api
  namespace: argocd
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # ⭐ Deploy SAU cả Prometheus và Argo Rollouts
spec:
  project: default
  source:
    repoURL: https://github.com/ddor2812-dev/gitops.git
    targetRevision: main
    path: k8s-api                      # ⭐ Trỏ tới thư mục k8s-api/ (KHÔNG phải k8s/)
  destination:
    server: https://kubernetes.default.svc
    namespace: demo
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

**Tại sao sync-wave là "2"?**

| Wave | Ứng dụng | Lý do |
| :---: | :--- | :--- |
| 1 | `kube-prometheus-stack`, `argo-rollouts` | Cần cài CRD trước (Rollout, ServiceMonitor, AnalysisTemplate) |
| 2 | `api` | Sử dụng CRD đã được cài ở wave 1. Nếu chạy song song → K8s không nhận diện được CRD → lỗi |

---

### 3.4. `app/app.py` — Mã nguồn Flask API

```python
import os
import random
import time
from flask import Flask, jsonify
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)

# ⭐ KHỞI TẠO PROMETHEUS METRICS
# Thư viện 'prometheus_flask_exporter' tự động:
# 1. Tạo endpoint /metrics để Prometheus scrape
# 2. Đếm số request, thời gian xử lý, mã HTTP trả về...
metrics = PrometheusMetrics(app)
metrics.info('app_info', 'Application info', version=os.environ.get('VERSION', 'v1'))

# ĐỌC CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG
# (các biến này được truyền vào từ file api.yaml trong k8s-api/)
VERSION = os.environ.get('VERSION', 'v1')      # Phiên bản API (v1, v2, v3...)
ERROR_RATE = float(os.environ.get('ERROR_RATE', '0'))  # Tỷ lệ lỗi giả lập (0 = không lỗi)

@app.route('/')
def hello():
    # ⭐ GIẢ LẬP LỖI — dùng để kiểm tra Canary Rollback
    # Nếu ERROR_RATE = 0.2, có 20% xác suất request sẽ trả về lỗi 500
    if ERROR_RATE > 0:
        if random.random() < ERROR_RATE:
            return jsonify({
                "status": "error",
                "message": "Internal Server Error (Simulated)",
                "version": VERSION
            }), 500     # ← Mã HTTP 500 → Prometheus ghi nhận là lỗi

    # Phản hồi thành công → Mã HTTP 200
    return jsonify({
        "status": "success",
        "message": f"Hello from Python Flask API {VERSION}",
        "version": VERSION
    })

@app.route('/healthz')
def healthz():
    # ⭐ HEALTH CHECK — Kubernetes dùng endpoint này để kiểm tra pod còn sống không
    # Nếu endpoint này trả lỗi → K8s đánh dấu pod là "NotReady" → không gửi traffic tới
    return jsonify({"status": "healthy", "version": VERSION}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)  # Lắng nghe trên cổng 8080
```

**Tại sao Flask API cần endpoint `/metrics`?**

Khi bạn truy cập `http://api:8080/metrics`, Flask sẽ trả về dữ liệu dạng text mà Prometheus hiểu được:

```
# Ví dụ output của /metrics
flask_http_request_total{method="GET",status="200"} 156.0
flask_http_request_total{method="GET",status="500"} 12.0
flask_http_request_duration_seconds_sum{method="GET"} 3.45
```

→ Prometheus đọc dữ liệu này và tính toán: tỷ lệ lỗi = 12 / (156 + 12) ≈ 7.1%. Nếu vượt ngưỡng SLO (5%) → kích hoạt cảnh báo.

---

### 3.5. `app/Dockerfile` — Đóng gói Flask API

```dockerfile
FROM python:3.12-slim                    # Image Python nhẹ (~50MB thay vì ~1GB)

WORKDIR /app                             # Thư mục làm việc trong container

# Cài đặt thư viện Python
# --no-cache-dir: không lưu cache pip → giảm kích thước image
RUN pip install --no-cache-dir flask prometheus-flask-exporter

COPY app.py .                            # Sao chép mã nguồn vào container

EXPOSE 8080                              # Khai báo cổng ứng dụng (mang tính tài liệu)

CMD ["python", "app.py"]                 # Lệnh khởi chạy khi container start
```

---

### 3.6. `k8s-api/api.yaml` — Rollout & Service cho Flask API

File này chứa **2 tài nguyên**, ngăn cách bởi dấu `---`:

**Tài nguyên 1: Rollout (thay thế cho Deployment)**

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout                         # ⭐ KHÔNG phải Deployment! Đây là CRD của Argo Rollouts
metadata:
  name: api
  namespace: demo
  annotations:
    argocd.argoproj.io/sync-wave: "1"
spec:
  replicas: 4                         # Tạo 4 pod API (nhiều pod = chịu tải tốt hơn)
  revisionHistoryLimit: 2             # Chỉ giữ lại 2 phiên bản cũ (tiết kiệm tài nguyên)
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api                      # ServiceMonitor sẽ tìm pod qua label này
    spec:
      containers:
      - name: api
        image: w9-api:1               # ⭐ Image được build cục bộ (Lab 2)
        imagePullPolicy: IfNotPresent  # Không pull từ registry → dùng image local
        ports:
        - containerPort: 8080
          name: http                  # ⭐ Đặt tên "http" để ServiceMonitor tham chiếu
        env:
        - name: VERSION
          value: "v1"                 # Phiên bản API — thay đổi giá trị này để kích hoạt Canary
        - name: ERROR_RATE
          value: "0"                  # 0 = không lỗi. Đổi thành "0.2" để giả lập 20% lỗi
        readinessProbe:
          httpGet:
            path: /healthz            # K8s gọi endpoint này để kiểm tra pod sẵn sàng
            port: 8080
          initialDelaySeconds: 5      # Chờ 5s sau khi pod khởi động mới bắt đầu kiểm tra
          periodSeconds: 5            # Kiểm tra mỗi 5 giây
        resources:
          requests:                   # Tài nguyên tối thiểu cần thiết
            memory: "64Mi"
            cpu: "50m"
          limits:                     # Tài nguyên tối đa được phép sử dụng
            memory: "128Mi"
            cpu: "200m"

  # ⭐ CHIẾN LƯỢC CANARY — Đây là phần quan trọng nhất!
  strategy:
    canary:
      analysis:
        templates:
        - templateName: success-rate  # Liên kết với AnalysisTemplate "success-rate"
                                      # Argo Rollouts sẽ tự tạo AnalysisRun khi bắt đầu Canary
      steps:
      - setWeight: 25                 # Bước 1: Chuyển 25% traffic sang phiên bản mới
      - pause:
          duration: 20s               # Bước 2: Tạm dừng 20s — AnalysisRun đo lường chất lượng
      - setWeight: 50                 # Bước 3: Nếu phân tích OK → tăng lên 50%
      - pause:
          duration: 20s               # Bước 4: Tạm dừng 20s — tiếp tục đo lường
                                      # Nếu sau bước 4 mà AnalysisRun vẫn OK → tự động lên 100%
```

**Tài nguyên 2: Service**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: demo
  labels:
    app: api                          # ⭐ Label này giúp ServiceMonitor nhận diện Service
spec:
  selector:
    app: api                          # Kết nối tới tất cả pod có label app=api
  ports:
  - name: http                       # ⭐ Tên port "http" — ServiceMonitor sẽ dùng tên này
    port: 8080
    targetPort: 8080
```

**Sơ đồ luồng Canary:**

```
Commit: VERSION="v2" → Git Push → Argo CD Sync

                    ┌────────── Service: api ──────────┐
                    │            (Port 8080)            │
                    └─────────────────┬────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────────┐
               │ (Argo Rollouts điều hướng traffic theo tỷ lệ)   │
               ▼                                                  ▼
 ┌───────────────────────────┐                   ┌───────────────────────────┐
 │      Pods Phiên bản v1    │                   │      Pods Phiên bản v2    │
 │       (75% Traffic)       │                   │       (25% Traffic)       │
 │  - w9-api:1               │                   │  - w9-api:2               │
 │  - Phục vụ ổn định        │                   │  - Đang thử nghiệm        │
 └───────────────────────────┘                   └───────────────────────────┘
                                                           ▲
                                                    AnalysisRun
                                                  đo lường mỗi 10s
                                                           │
                                                    ┌──────┴───────┐
                                                    │  Prometheus  │
                                                    │ (scrape /metrics) │
                                                    └──────────────┘
```

---

### 3.7. `k8s-api/servicemonitor.yaml` — Cấu hình Prometheus Scrape

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor                    # CRD của Prometheus Operator
metadata:
  name: api-monitor
  namespace: demo
  labels:
    release: kube-prometheus-stack      # ⭐ Label này phải khớp với Prometheus Operator
                                        # (mặc dù ta đã tắt filter bằng
                                        # serviceMonitorSelectorNilUsesHelmValues: false,
                                        # thêm label này cho chắc chắn)
spec:
  selector:
    matchLabels:
      app: api                          # ⭐ Tìm Service nào có label app=api để scrape
  endpoints:
  - port: http                          # ⭐ Dùng tên port "http" đã khai báo trong Service
    path: /metrics                      # Đường dẫn chứa metric của Flask
    interval: 15s                       # Prometheus sẽ scrape mỗi 15 giây
```

**Giải thích bằng ngôn ngữ đời thường:**

File này nói với Prometheus rằng: "Hãy tìm Service nào trong namespace `demo` có label `app: api`, rồi cứ mỗi 15 giây, đi tới đường dẫn `/metrics` trên port `http` (8080) của Service đó để thu thập số liệu."

---

### 3.8. `k8s-api/analysistemplate.yaml` — Khuôn mẫu Đánh giá Canary

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata:
  name: success-rate
  namespace: demo
spec:
  metrics:
  - name: success-rate
    interval: 10s                     # ⭐ Đo lường mỗi 10 giây

    # ⭐ ĐIỀU KIỆN THÀNH CÔNG (SLO — Service Level Objective)
    # Tỷ lệ thành công phải >= 95% (tức tỷ lệ lỗi < 5%)
    successCondition: result[0] >= 0.95

    failureLimit: 3                   # ⭐ Cho phép tối đa 3 lần đo thất bại liên tiếp
                                      # Nếu vượt quá 3 lần → AnalysisRun = Failed → Rollback

    provider:
      prometheus:
        # Địa chỉ Prometheus bên trong cluster (Service DNS)
        address: http://kube-prometheus-stack-prometheus.monitoring.svc:9090
        query: |
          # ⭐ CÔNG THỨC TÍNH TỶ LỆ THÀNH CÔNG:
          #
          # Tử số: Tổng tốc độ request KHÔNG phải lỗi 5xx trong 1 phút
          # Mẫu số: Tổng tốc độ TẤT CẢ request trong 1 phút
          # Kết quả: Con số từ 0 đến 1 (ví dụ: 0.95 = 95% thành công)
          #
          # "or vector(1)": Nếu chưa có request nào (mẫu số = 0),
          # trả về 1 (100% thành công) → tránh lỗi chia cho 0
          sum(rate(flask_http_request_total{status!~"5.*",job="api",namespace="demo"}[1m]))
          /
          sum(rate(flask_http_request_total{job="api",namespace="demo"}[1m])) or vector(1)
```

**Giải thích truy vấn Prometheus (PromQL):**

| Phần | Ý nghĩa |
| :--- | :--- |
| `flask_http_request_total` | Metric tổng số request do Flask xuất ra |
| `{status!~"5.*"}` | Lọc bỏ các request có status code bắt đầu bằng 5 (500, 502, 503...) |
| `{job="api"}` | Chỉ lấy metric từ job tên "api" (ServiceMonitor tạo ra) |
| `{namespace="demo"}` | Chỉ lấy metric từ namespace "demo" |
| `rate(...[1m])` | Tính tốc độ thay đổi trong 1 phút gần nhất |
| `sum(...)` | Cộng tổng từ tất cả các pod |
| `or vector(1)` | Giá trị mặc định = 1 nếu không có dữ liệu |

---

### 3.9. `k8s-api/prometheusrule.yaml` — Quy tắc Cảnh báo

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule                    # CRD của Prometheus Operator
metadata:
  name: api-alerts
  namespace: demo
  labels:
    release: kube-prometheus-stack      # Phải khớp để Prometheus nhận diện
spec:
  groups:
  - name: api.rules
    rules:
    - alert: ApiHighErrorRate           # ⭐ TÊN CẢNH BÁO — hiển thị trên Alertmanager UI
      expr: |
        # Công thức: Tỷ lệ lỗi HTTP 5xx / Tổng request
        # Nếu kết quả > 0.05 (5%) → kích hoạt cảnh báo
        (sum(rate(flask_http_request_total{status=~"5..",job="api",namespace="demo"}[1m]))
        /
        sum(rate(flask_http_request_total{job="api",namespace="demo"}[1m])) or vector(0)) > 0.05
      for: 10s                          # ⭐ Chỉ kích hoạt nếu lỗi KÉO DÀI trên 10 giây
                                        # Tránh cảnh báo giả do lỗi thoáng qua
      labels:
        severity: critical              # Mức độ nghiêm trọng — dùng để lọc/định tuyến
      annotations:
        summary: "High HTTP 5xx error rate detected on API"
        description: "The HTTP 5xx error rate of API pods is {{ $value | humanizePercentage }} which is higher than the 5% threshold."
```

**Sự khác biệt giữa AnalysisTemplate và PrometheusRule:**

| | AnalysisTemplate | PrometheusRule |
| :--- | :--- | :--- |
| **Ai quản lý?** | Argo Rollouts | Prometheus |
| **Mục đích?** | Quyết định rollback tự động | Gửi cảnh báo cho con người |
| **Ngưỡng?** | 95% thành công (SLO) | 5% lỗi (Alert) |
| **Hành động?** | Abort Canary + Rollback | Gửi email qua AlertManager |

Cả hai đều truy vấn Prometheus nhưng phục vụ mục đích khác nhau: một cái để **máy quyết định**, một cái để **người biết**.

---

## 4. Luồng Hoạt Động Tổng Thể — Giám Sát & Canary

Dưới đây là sơ đồ mô tả cách hệ thống hoạt động từ đầu đến cuối sau khi hoàn thành cả 4 Lab:

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                              CỤM KUBERNETES (Minikube w9)                               │
│                                                                                          │
│  ┌──────────────────── namespace: argo-rollouts ─────────────────────┐                   │
│  │  Argo Rollouts Controller                                        │                   │
│  │  → Theo dõi tài nguyên loại "Rollout" trong toàn cluster         │                   │
│  │  → Điều khiển quá trình Canary (set weight, create AnalysisRun)  │                   │
│  └──────────────────────────────────────────────────────────────────┘                   │
│                                                                                          │
│  ┌──────────────────── namespace: monitoring ────────────────────────┐                   │
│  │                                                                   │                   │
│  │  ┌─ Prometheus ──┐  ┌─ Grafana ──┐  ┌─ AlertManager ────────┐   │                   │
│  │  │ Scrape /metrics│  │ Dashboard  │  │ Gửi email khi Alert  │   │                   │
│  │  │ mỗi 15 giây   │  │ trực quan  │  │ chuyển sang Firing    │   │                   │
│  │  └───────┬────────┘  └────────────┘  └──────────┬────────────┘   │                   │
│  │          │                                      │                 │                   │
│  └──────────│──────────────────────────────────────│─────────────────┘                   │
│             │ ① Scrape                             │ ⑤ Gửi email                        │
│             │ (ServiceMonitor)                     │ ddor2812@gmail.com                  │
│             ▼                                      ▼                                     │
│  ┌──────────────────── namespace: demo ──────────────────────────────┐                   │
│  │                                                                   │                   │
│  │  ┌── Rollout: api ──────────────────────────────────────────────┐ │                   │
│  │  │                                                              │ │                   │
│  │  │  ② Canary Strategy                                          │ │                   │
│  │  │  ┌──────────────┐  ┌──────────────┐                         │ │                   │
│  │  │  │ Pods v1 (75%)│  │ Pods v2 (25%)│                         │ │                   │
│  │  │  │ w9-api:1     │  │ w9-api:2     │                         │ │                   │
│  │  │  └──────────────┘  └──────────────┘                         │ │                   │
│  │  │                                                              │ │                   │
│  │  │  ③ AnalysisRun ←── AnalysisTemplate: success-rate           │ │                   │
│  │  │     Truy vấn Prometheus mỗi 10s                             │ │                   │
│  │  │     SLO: success_rate >= 95%                                │ │                   │
│  │  │     ✅ Đạt → 25% → 50% → 100% (Tự động hoàn tất)          │ │                   │
│  │  │     ❌ Thất bại (3 lần) → ABORT + Rollback về v1           │ │                   │
│  │  └──────────────────────────────────────────────────────────────┘ │                   │
│  │                                                                   │                   │
│  │  ④ PrometheusRule: ApiHighErrorRate                              │                   │
│  │     Nếu tỷ lệ lỗi > 5% trong 10s → Alert Firing → AlertManager │                   │
│  │                                                                   │                   │
│  └───────────────────────────────────────────────────────────────────┘                   │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘
                             ▲
                             │ Git Push (thay đổi VERSION/ERROR_RATE)
                             │
                    ┌────────┴─────────┐
                    │ GitHub Repository │
                    │ (nhánh main)     │
                    │                  │
                    │ k8s-api/         │
                    │   api.yaml       │ ◄── Argo CD quét mỗi ~3 phút
                    └──────────────────┘
```

### Quy trình khi bạn nâng cấp phiên bản API:

| Bước | Điều gì xảy ra? |
| :---: | :--- |
| **1** | Bạn sửa `VERSION: "v2"` trong file `k8s-api/api.yaml` rồi push lên GitHub. |
| **2** | Argo CD phát hiện thay đổi, đồng bộ file `api.yaml` mới vào cluster. |
| **3** | Argo Rollouts Controller nhận thấy `Rollout` thay đổi → khởi động Canary: tạo pod mới với image `v2`, chuyển 25% traffic sang pod mới. |
| **4** | Đồng thời, Argo Rollouts tạo một `AnalysisRun` dựa trên `AnalysisTemplate` "success-rate". |
| **5** | `AnalysisRun` cứ mỗi 10 giây lại truy vấn Prometheus: "Tỷ lệ thành công hiện tại là bao nhiêu?" |
| **6a** | ✅ Nếu >= 95%: Sau 20s tăng lên 50%, sau thêm 20s tăng lên 100%. **Hoàn tất!** |
| **6b** | ❌ Nếu < 95% quá 3 lần: AnalysisRun = Failed → Argo Rollouts **tự động hủy bỏ** Canary, thu hồi pod mới, traffic quay về 100% bản cũ. **Rollback hoàn tất!** |
| **7** | Đồng thời, nếu tỷ lệ lỗi > 5%, `PrometheusRule` kích hoạt Alert → AlertManager gửi email cảnh báo cho bạn. |

---

## 5. Chi Tiết Từng Bài Lab và Các Bước Thực Hiện

### Điều kiện tiên quyết

Trước khi bắt đầu, hãy chắc chắn bạn đã hoàn thành các bước trong `README.md`:

- ✅ Cụm Kubernetes đang chạy (Minikube profile `w9` hoặc tương đương)
- ✅ Argo CD đã được cài đặt trong namespace `argocd`
- ✅ Root App đã được apply: `kubectl apply -f argocd/root.yaml`
- ✅ Các ứng dụng `web`, `frontend`, `backend` đang hoạt động bình thường
- ✅ `kubectl` đã được kết nối tới cluster

---

### Lab 1: Cài đặt Prometheus Stack & Argo Rollouts qua GitOps

**Mục tiêu**: Cài đặt bộ công cụ giám sát (Prometheus + Grafana + AlertManager) và Argo Rollouts Controller vào cluster thông qua mô hình App-of-Apps — **không dùng lệnh `helm install` thủ công**.

---

#### Bước 1.1: Tạo file cấu hình Argo CD cho Prometheus Stack

Tạo file `argocd/apps/kube-prometheus-stack.yaml` với nội dung như đã mô tả ở [mục 3.1](#31-argocdappskube-prometheus-stackyaml--cài-đặt-prometheus-grafana--alertmanager).

> **Lưu ý quan trọng**: Phải có `ServerSideApply=true` trong `syncOptions` để tránh lỗi CRD quá lớn. Xem [Phụ lục](#6-phụ-lục-xử-lý-lỗi-phổ-biến) nếu gặp lỗi.

#### Bước 1.2: Tạo file cấu hình Argo CD cho Argo Rollouts

Tạo file `argocd/apps/argo-rollouts.yaml` với nội dung như đã mô tả ở [mục 3.2](#32-argocdappsargo-rolloutsyaml--cài-đặt-argo-rollouts-controller).

#### Bước 1.3: Commit và Push lên GitHub

```bash
git add argocd/apps/kube-prometheus-stack.yaml argocd/apps/argo-rollouts.yaml
git commit -m "feat: add prometheus stack and argo rollouts via app-of-apps"
git push origin main
```

#### Bước 1.4: Chờ Root App phát hiện và tạo ứng dụng mới

Root App sẽ tự động quét thư mục `argocd/apps/`, phát hiện 2 file mới, và tạo ra 2 ứng dụng con trên Argo CD. Nếu muốn nhanh hơn:

```bash
# Yêu cầu Argo CD quét Git ngay lập tức
kubectl annotate application root -n argocd argocd.argoproj.io/refresh=normal --overwrite
```

#### Bước 1.5: Kiểm tra trạng thái

```bash
# Xem tất cả ứng dụng Argo CD
kubectl get application -n argocd

# Kết quả mong đợi (có thể mất vài phút):
# NAME                      SYNC STATUS   HEALTH STATUS
# root                      Synced        Healthy
# web                       Synced        Healthy
# frontend                  Synced        Healthy
# backend                   Synced        Healthy
# kube-prometheus-stack      Synced        Healthy     ← MỚI
# argo-rollouts             Synced        Healthy     ← MỚI
```

```bash
# Kiểm tra pod Prometheus đã chạy chưa
kubectl get pods -n monitoring

# Kết quả mong đợi: Nhiều pod đang Running
# (prometheus-kube-prometheus-stack-prometheus-0, grafana, alertmanager, node-exporter...)
```

```bash
# Kiểm tra pod Argo Rollouts Controller
kubectl get pods -n argo-rollouts

# Kết quả mong đợi: 1 pod "argo-rollouts-xxx" đang Running
```

#### Bước 1.6 (tuỳ chọn): Truy cập Grafana để kiểm tra

```bash
# Port-forward tới Grafana UI
kubectl port-forward svc/kube-prometheus-stack-grafana -n monitoring 3000:80
```

Mở trình duyệt: [http://localhost:3000](http://localhost:3000)
- Tài khoản: `admin`
- Mật khẩu: `admin`

---

### Lab 2: Xây dựng và Docker hóa Flask API có Metrics

**Mục tiêu**: Xây dựng một Flask API đơn giản, có xuất Prometheus metrics, hỗ trợ giả lập lỗi, và nạp Docker image vào cluster Minikube.

---

#### Bước 2.1: Tạo mã nguồn Flask API

Tạo thư mục `app/` và file `app/app.py` với nội dung như đã mô tả ở [mục 3.4](#34-appapppy--mã-nguồn-flask-api).

**Điểm quan trọng trong code:**
- Thư viện `prometheus_flask_exporter` **tự động** tạo endpoint `/metrics` và đếm số request theo HTTP method + status code.
- Biến môi trường `ERROR_RATE` cho phép **giả lập lỗi có kiểm soát** — rất quan trọng để test Canary rollback ở Lab 4.
- Endpoint `/healthz` phục vụ cho Kubernetes `readinessProbe` — giúp K8s biết pod đã sẵn sàng nhận traffic chưa.

#### Bước 2.2: Tạo Dockerfile

Tạo file `app/Dockerfile` với nội dung như đã mô tả ở [mục 3.5](#35-appdockerfile--đóng-gói-flask-api).

#### Bước 2.3: Build Docker image và nạp vào Minikube

```bash
# Bước 1: Build Docker image cục bộ với tag "w9-api:1"
docker build -t w9-api:1 app/

# Bước 2: Nạp image vào cluster Minikube
# (Minikube chạy Docker riêng bên trong VM, nên cần "load" image từ máy host vào)
minikube -p w9 image load w9-api:1
```

> **Tại sao không push lên Docker Hub?** Trong bài lab này, chúng ta load trực tiếp vào Minikube để đơn giản hóa. Trong thực tế, bạn sẽ push image lên một Container Registry (Docker Hub, GitHub Container Registry, AWS ECR...) và cập nhật tag image trong file YAML.

#### Bước 2.4: Kiểm tra image đã được nạp

```bash
# Liệt kê các image trong Minikube
minikube -p w9 image list | grep w9-api

# Kết quả mong đợi:
# docker.io/library/w9-api:1
```

---

### Lab 3: Triển khai Canary Rollout & Cấu hình ServiceMonitor

**Mục tiêu**: Khai báo tài nguyên dạng `Rollout` (thay thế cho `Deployment`), cấu hình ServiceMonitor để Prometheus scrape API metrics, tạo AnalysisTemplate cho đánh giá tự động, và đăng ký ứng dụng `api` với Argo CD.

---

#### Bước 3.1: Tạo thư mục và các file cấu hình K8s

Tạo thư mục `k8s-api/` và 4 file bên trong:

| File | Mục đích | Tham chiếu chi tiết |
| :--- | :--- | :--- |
| `api.yaml` | Rollout + Service | [Mục 3.6](#36-k8s-apiapiyaml--rollout--service-cho-flask-api) |
| `servicemonitor.yaml` | ServiceMonitor cho Prometheus | [Mục 3.7](#37-k8s-apiservicemonitoryaml--cấu-hình-prometheus-scrape) |
| `analysistemplate.yaml` | AnalysisTemplate đo lường SLO | [Mục 3.8](#38-k8s-apianalysistemplateyaml--khuôn-mẫu-đánh-giá-canary) |
| `prometheusrule.yaml` | PrometheusRule cảnh báo lỗi | [Mục 3.9](#39-k8s-apiprometheusruleyaml--quy-tắc-cảnh-báo) |

#### Bước 3.2: Đăng ký ứng dụng API với Argo CD

Tạo file `argocd/apps/api.yaml` với nội dung như đã mô tả ở [mục 3.3](#33-argocdappsapiyaml--khai-báo-ứng-dụng-flask-api).

#### Bước 3.3: Commit và Push lên GitHub

```bash
git add k8s-api/ argocd/apps/api.yaml
git commit -m "feat: deploy canary rollout with analysis and monitoring"
git push origin main
```

#### Bước 3.4: Kiểm tra trạng thái triển khai

```bash
# Xem ứng dụng API trên Argo CD
kubectl get application api -n argocd

# Kết quả mong đợi:
# NAME   SYNC STATUS   HEALTH STATUS
# api    Synced        Healthy

# Kiểm tra pod API đã chạy chưa
kubectl get pods -n demo -l app=api

# Kết quả mong đợi: 4 pod đang Running
# api-xxxxx-yyy   1/1   Running   0   30s
# api-xxxxx-zzz   1/1   Running   0   30s
# api-xxxxx-aaa   1/1   Running   0   30s
# api-xxxxx-bbb   1/1   Running   0   30s
```

#### Bước 3.5: Kiểm tra API hoạt động

```bash
# Port-forward tới API Service
kubectl port-forward svc/api -n demo 8085:8080

# Gọi API
curl http://localhost:8085/
# → {"message":"Hello from Python Flask API v1","status":"success","version":"v1"}

# Kiểm tra endpoint metrics
curl http://localhost:8085/metrics | head -5
# → flask_http_request_total{method="GET",status="200"} 1.0
```

#### Bước 3.6: Kiểm tra Prometheus đã scrape được API

```bash
# Port-forward tới Prometheus UI
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9095:9090
```

Mở trình duyệt: [http://localhost:9095](http://localhost:9095)

1. Trong ô tìm kiếm, gõ: `flask_http_request_total`
2. Nhấn **Execute**
3. Nếu thấy dữ liệu → Prometheus đã scrape thành công ✅

---

### Lab 4: Thực Hiện Canary Deployment & Giám Sát Trực Quan

**Mục tiêu**: Thực hiện 3 kịch bản thực tế để chứng minh sức mạnh của hệ thống GitOps + Progressive Delivery + Observability:

| Kịch bản | Mô tả | Kết quả mong đợi |
| :---: | :--- | :--- |
| 1 | Nâng cấp bản tốt (v1 → v2) | Canary tự động hoàn tất 100% |
| 2 | Nâng cấp bản lỗi (v2 → v3 với 20% lỗi) | Canary tự động hủy bỏ + Rollback |
| 3 | Rollback thủ công qua Git | Khôi phục < 5 phút |

---

#### Bước 4.1: Mở các Port-forward cần thiết

Mở **nhiều tab terminal** và chạy từng lệnh sau:

**Tab 1 — API Service (Port 8085):**
```bash
kubectl port-forward svc/api -n demo 8085:8080
```

**Tab 2 — Prometheus UI (Port 9095):**
```bash
kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9095:9090
```

**Tab 3 — AlertManager UI (Port 9093):**
```bash
kubectl port-forward svc/kube-prometheus-stack-alertmanager -n monitoring 9093:9093
```

---

#### Bước 4.2: Cách theo dõi Rollout trực quan

Bạn có **2 cách** để theo dõi quá trình Canary realtime:

**Cách 1 (Khuyên dùng — Không cần cài thêm gì):** Mở **Argo CD UI** tại [http://localhost:8080](http://localhost:8080), click vào ứng dụng **`api`**. Bạn sẽ thấy sơ đồ khối cực kỳ chi tiết hiển thị từng bước Canary, các Pod bản cũ/mới và tiến trình `AnalysisRun` theo thời gian thực.

**Cách 2 (CLI — Cần cài plugin):** Cài đặt plugin `kubectl-argo-rollouts`:

```bash
# Cách A: Qua Homebrew (khuyên dùng cho macOS)
brew install argoproj/tap/kubectl-argo-rollouts

# Cách B: Tải trực tiếp cho macOS Apple Silicon (M1/M2/M3/M4)
curl -LO https://github.com/argoproj/argo-rollouts/releases/latest/download/kubectl-argo-rollouts-darwin-arm64
chmod +x ./kubectl-argo-rollouts-darwin-arm64
sudo mv ./kubectl-argo-rollouts-darwin-arm64 /usr/local/bin/kubectl-argo-rollouts
```

Sau khi cài xong, chạy lệnh theo dõi (mở thêm 1 tab terminal):

```bash
kubectl argo rollouts get rollout api -n demo --watch
```

---

#### Bước 4.3: Kịch bản 1 — Nâng cấp Thành công (Bản tốt → 100% tự động)

**Mục tiêu**: Chứng minh khi phiên bản mới hoạt động hoàn hảo, hệ thống tự động hoàn tất Canary mà không cần can thiệp.

**Thực hiện:**

1. Mở file `k8s-api/api.yaml`, sửa giá trị `VERSION` từ `"v1"` thành `"v2"`. **Giữ nguyên** `ERROR_RATE` bằng `"0"`.

2. Commit và push:
    ```bash
    git add k8s-api/api.yaml && git commit -m "upgrade: api to v2" && git push origin main
    ```

3. **Quan sát trên Argo CD UI hoặc CLI:**

    ```
    Thời gian    Hành động                          Trạng thái
    ─────────    ───────────────────────────────     ──────────────────
    T+0s         Argo CD sync → tạo pod v2          Canary: 25% (v2)
    T+0s         AnalysisRun bắt đầu                Running
    T+10s        AnalysisRun đo: 100% thành công    ✅ Measurement 1: Pass
    T+20s        AnalysisRun đo: 100% thành công    ✅ Measurement 2: Pass
    T+20s        Tăng weight → 50%                  Canary: 50% (v2)
    T+30s        AnalysisRun đo: 100% thành công    ✅ Measurement 3: Pass
    T+40s        AnalysisRun đo: 100% thành công    ✅ Measurement 4: Pass
    T+40s        Tăng weight → 100%                 ✅ Canary HOÀN TẤT
    T+40s        Xóa pod v1 cũ                      Stable: 100% (v2)
    ```

4. **Kiểm tra kết quả:**
    ```bash
    curl http://localhost:8085/
    # → {"message":"Hello from Python Flask API v2","status":"success","version":"v2"}
    ```

---

#### Bước 4.4: Kịch bản 2 — Bản lỗi tự động Hủy bỏ (Auto-abort & Auto-rollback)

**Mục tiêu**: Chứng minh khi phiên bản mới có lỗi, hệ thống **tự phát hiện** và **tự rollback** mà không cần con người can thiệp.

**Thực hiện:**

1. Mở file `k8s-api/api.yaml`, sửa `VERSION` thành `"v3"` và đặt `ERROR_RATE` thành `"0.2"` (giả lập 20% request trả về lỗi HTTP 500).

2. Commit và push:
    ```bash
    git add k8s-api/api.yaml && git commit -m "upgrade: api to v3 with error simulation" && git push origin main
    ```

3. **Kích hoạt sinh traffic** — mở thêm 1 tab terminal và chạy:
    ```bash
    # Gửi request liên tục để tạo metric cho Prometheus
    while true; do curl -s http://localhost:8085/ | grep version; sleep 0.2; done
    ```

    > **Tại sao cần bước này?** Prometheus chỉ có dữ liệu khi có request thực tế. Nếu không có traffic, AnalysisTemplate sẽ dùng giá trị mặc định `vector(1)` = 100% thành công → không phát hiện được lỗi.

4. **Quan sát hệ thống tự bảo vệ:**

    ```
    Thời gian    Hành động                              Trạng thái
    ─────────    ───────────────────────────────────     ──────────────────────
    T+0s         Argo CD sync → tạo pod v3              Canary: 25% (v3)
    T+0s         AnalysisRun bắt đầu                    Running
    T+10s        Đo: ~80% thành công (dưới 95%)         ❌ Failure 1
    T+20s        Đo: ~80% thành công                    ❌ Failure 2
    T+30s        Đo: ~80% thành công                    ❌ Failure 3 (vượt failureLimit!)
    T+30s        AnalysisRun = FAILED                   🚨 AUTO-ABORT
    T+30s        Rollback tức thì                       Traffic: 100% v2 (an toàn)
    T+30s        Pod v3 bị xóa                          Stable: 100% (v2)
    ```

5. **Kiểm tra AlertManager:** Mở trình duyệt tại [http://localhost:9093](http://localhost:9093)
   - Bạn sẽ thấy cảnh báo **`ApiHighErrorRate`** ở trạng thái **Firing** (màu đỏ).
   - AlertManager sẽ gửi email tới `ddor2812@gmail.com` thông báo chất lượng dịch vụ sụt giảm.

6. **Kiểm tra API đã quay về bản cũ:**
    ```bash
    curl http://localhost:8085/
    # → {"message":"Hello from Python Flask API v2","status":"success","version":"v2"}
    # ← Đã rollback về v2 an toàn!
    ```

---

#### Bước 4.5: Kịch bản 3 — Rollback thủ công qua Git cực nhanh (< 5 phút)

**Mục tiêu**: Nếu bạn lỡ push một thay đổi lỗi lên Git và muốn khôi phục an toàn — chỉ cần 2 lệnh Git.

**Thực hiện:**

1. Chạy lệnh khôi phục Git commit trước đó:
    ```bash
    git revert HEAD --no-edit
    ```
    > Lệnh `git revert` tạo ra một commit **mới** với nội dung ngược lại commit trước. Nó KHÔNG xóa lịch sử Git — an toàn hơn nhiều so với `git reset`.

2. Push code lên nhánh chính:
    ```bash
    git push origin main
    ```

3. **Kết quả:** Argo CD tự động phát hiện thay đổi mới trên Git và đồng bộ cụm K8s về đúng trạng thái an toàn. Toàn bộ quy trình diễn ra hoàn toàn tự động chỉ trong vòng chưa đầy 2 phút, đảm bảo tính nhất quán (no drift) giữa Git và hệ thống thực tế!

```
Developer                     GitHub                    Argo CD                K8s Cluster
    │                            │                         │                       │
    │── git revert HEAD ────────▶│                         │                       │
    │── git push ───────────────▶│                         │                       │
    │                            │◀── quét mỗi ~3 phút ───│                       │
    │                            │── phát hiện thay đổi ──▶│                       │
    │                            │                         │── sync YAML mới ─────▶│
    │                            │                         │                       │── rollback pods
    │                            │                         │                       │── khôi phục config
    │                            │                         │◀── báo cáo Healthy ───│
    │                            │                         │                       │
    │◀──── Hoàn tất (< 2 phút) ──────────────────────────────────────────────────│
```

---

## 6. Phụ Lục: Xử Lý Lỗi Phổ Biến

### 6.1. Lỗi CRD quá lớn khi cài Prometheus Stack (Too long annotations)

#### Mô tả lỗi

Khi Argo CD đồng bộ Helm Chart `kube-prometheus-stack`, ứng dụng có thể bị kẹt ở trạng thái **OutOfSync** với thông báo:

```
CustomResourceDefinition.apiextensions.k8s.io "thanosrulers.monitoring.coreos.com" is invalid:
metadata.annotations: Too long: may not be more than 262144 bytes
```

#### Nguyên nhân

Theo mặc định, `kubectl apply` lưu cấu hình cũ vào trường annotation `kubectl.kubernetes.io/last-applied-configuration`. Do các file định nghĩa CRD của Prometheus quá lớn (hàng trăm KB), dung lượng annotation vượt quá giới hạn 256KB của Kubernetes.

#### Cách khắc phục từng bước

**Bước 1: Đảm bảo ServerSideApply đã được bật**

Kiểm tra file `argocd/apps/kube-prometheus-stack.yaml` có chứa:

```yaml
syncOptions:
- ServerSideApply=true
```

Nếu chưa có, thêm vào rồi commit + push lên Git.

**Bước 2: Dừng tiến trình Retry bị kẹt trên Argo CD**

Argo CD có thể đang tự động thử lại (retry) lệnh đồng bộ cũ đã bị lỗi. Xóa trạng thái này:

```bash
kubectl patch application kube-prometheus-stack -n argocd \
  --type json -p '[{"op": "remove", "path": "/operation"}]'
```

**Bước 3: Cài đặt thủ công các CRD lớn bằng Server-Side Apply**

Nếu Argo CD vẫn gặp khó khăn khi khởi tạo CRD lần đầu, chạy trực tiếp:

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagerconfigs.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagers.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheusagents.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_scrapeconfigs.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_thanosrulers.yaml
```

**Bước 4: Yêu cầu Argo CD đồng bộ lại**

```bash
kubectl annotate application kube-prometheus-stack -n argocd \
  argocd.argoproj.io/refresh=hard --overwrite
```

---

### 6.2. Lỗi ImagePullBackOff cho image w9-api

#### Mô tả

Pod API bị kẹt ở trạng thái `ImagePullBackOff` hoặc `ErrImagePull`.

#### Nguyên nhân

Image `w9-api:1` chưa được load vào Minikube, hoặc `imagePullPolicy` được đặt thành `Always`.

#### Cách khắc phục

```bash
# 1. Kiểm tra image đã có trong Minikube chưa
minikube -p w9 image list | grep w9-api

# 2. Nếu chưa có, build và load lại
docker build -t w9-api:1 app/
minikube -p w9 image load w9-api:1

# 3. Đảm bảo imagePullPolicy là IfNotPresent (KHÔNG phải Always)
# Kiểm tra trong file k8s-api/api.yaml:
#   imagePullPolicy: IfNotPresent
```

---

### 6.3. ServiceMonitor không được Prometheus phát hiện

#### Mô tả

Prometheus UI không hiển thị metric `flask_http_request_total` mặc dù API đã chạy.

#### Cách kiểm tra và khắc phục

```bash
# 1. Kiểm tra ServiceMonitor đã được tạo chưa
kubectl get servicemonitor -n demo

# 2. Kiểm tra Prometheus config đã nhận ServiceMonitor chưa
# Vào Prometheus UI → Status → Targets
# Tìm kiếm "api" trong danh sách targets

# 3. Đảm bảo cấu hình Prometheus cho phép scrape mọi ServiceMonitor:
# Trong kube-prometheus-stack.yaml phải có:
#   serviceMonitorSelectorNilUsesHelmValues: false
```

---

### 6.4. Plugin kubectl-argo-rollouts không hoạt động

#### Mô tả

```
error: unknown command "argo" for "kubectl"
```

#### Cách khắc phục

Plugin chưa được cài đặt hoặc cài không đúng cách. Thay vào đó, hãy dùng **Argo CD UI** (Cách 1 ở [Bước 4.2](#bước-42-cách-theo-dõi-rollout-trực-quan)) — nó cung cấp giao diện trực quan tương đương mà không cần cài thêm gì.

Nếu vẫn muốn dùng CLI:

```bash
# macOS (Homebrew)
brew install argoproj/tap/kubectl-argo-rollouts

# Kiểm tra cài đặt thành công
kubectl argo rollouts version
```
