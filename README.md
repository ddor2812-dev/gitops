# Tài Liệu Chi Tiết Dự Án GitOps — Mô Hình App-of-Apps

---

## Mục Lục

1. [Giải thích các khái niệm cơ bản](#1-giải-thích-các-khái-niệm-cơ-bản)
2. [Cấu trúc thư mục dự án](#2-cấu-trúc-thư-mục-dự-án)
3. [Giải thích chi tiết từng file](#3-giải-thích-chi-tiết-từng-file)
4. [Luồng hoạt động tổng thể — Root App quản lý tất cả](#4-luồng-hoạt-động-tổng-thể--root-app-quản-lý-tất-cả)
5. [Sync Waves — Thứ tự triển khai tài nguyên](#5-sync-waves--thứ-tự-triển-khai-tài-nguyên)
6. [Luồng giao tiếp Frontend ↔ Backend](#6-luồng-giao-tiếp-frontend--backend)
7. [CI Pipeline — Kiểm tra tự động khi tạo Pull Request](#7-ci-pipeline--kiểm-tra-tự-động-khi-tạo-pull-request)
8. [Hướng dẫn triển khai từng bước](#8-hướng-dẫn-triển-khai-từng-bước)

---

## 1. Giải Thích Các Khái Niệm Cơ Bản

Trước khi đi vào chi tiết, hãy hiểu rõ các thuật ngữ quan trọng:

### GitOps là gì?

GitOps là một phương pháp vận hành hạ tầng và ứng dụng mà trong đó **Git (GitHub) là nguồn sự thật duy nhất** (Single Source of Truth). Nghĩa là:

- Bạn **KHÔNG** phải chạy `kubectl apply` thủ công mỗi khi muốn cập nhật ứng dụng.
- Thay vào đó, bạn chỉ cần **sửa file YAML trên Git → push lên GitHub**.
- Một công cụ tên là **Argo CD** sẽ tự động phát hiện thay đổi và cập nhật cụm Kubernetes cho bạn.

> **Ví dụ thực tế**: Bạn muốn tăng số lượng pod từ 2 lên 4. Thay vì gõ lệnh `kubectl scale`, bạn chỉ cần sửa `replicas: 4` trong file YAML trên GitHub. Argo CD sẽ tự phát hiện và thực hiện thay đổi đó.

### Argo CD là gì?

Argo CD là một công cụ chạy bên trong cụm Kubernetes. Nhiệm vụ của nó là:

1. **Theo dõi** một kho lưu trữ Git (ví dụ: GitHub repo của bạn).
2. **So sánh** cấu hình trong Git với trạng thái thực tế trên cụm Kubernetes.
3. Nếu phát hiện **khác biệt** → tự động đồng bộ (sync) để cụm Kubernetes khớp với Git.

### Application (Ứng dụng Argo CD) là gì?

Trong Argo CD, một `Application` là một đơn vị cấu hình cho Argo CD biết:
- **Lấy code ở đâu?** → `source.repoURL` (địa chỉ GitHub) + `source.path` (thư mục chứa file YAML)
- **Triển khai vào đâu?** → `destination.server` (cụm K8s nào) + `destination.namespace` (namespace nào)
- **Tự động đồng bộ không?** → `syncPolicy.automated` (có thì tự đồng bộ, không thì phải bấm tay)

### App-of-Apps là gì?

Thông thường, mỗi lần thêm một ứng dụng mới, bạn phải chạy `kubectl apply` thủ công để đăng ký ứng dụng đó với Argo CD. Rất bất tiện!

**App-of-Apps** là một kỹ thuật giải quyết vấn đề này:
- Bạn tạo **MỘT** ứng dụng gốc duy nhất gọi là **Root App**.
- Root App không triển khai pod hay service gì cả. Nó chỉ có nhiệm vụ **quét một thư mục trên Git** (ở đây là `argocd/apps/`).
- Trong thư mục đó, bạn đặt các file YAML khai báo các ứng dụng con (frontend, backend, web...).
- Root App sẽ tự động đọc các file đó và **tạo ra các ứng dụng con** trên Argo CD.

> **Lợi ích**: Khi bạn muốn thêm một ứng dụng mới (ví dụ: `monitoring`), bạn chỉ cần tạo thêm 1 file `monitoring.yaml` trong thư mục `argocd/apps/` rồi push lên Git. Root App sẽ tự phát hiện và tạo ứng dụng mới mà bạn **không cần chạy bất kỳ lệnh kubectl nào**.

---

## 2. Cấu Trúc Thư Mục Dự Án

```
gitops/                          ← Thư mục gốc của kho lưu trữ Git
│
├── README.md                    ← File tài liệu bạn đang đọc
│
├── .github/workflows/
│   └── validate.yml             ← CI Pipeline: tự động kiểm tra cú pháp YAML khi tạo PR
│
├── argocd/                      ← CẤU HÌNH ARGO CD (nói cho Argo CD biết phải làm gì)
│   │
│   ├── root.yaml                ← ỨNG DỤNG GỐC — điểm khởi đầu của mọi thứ
│   │                               Nó quét thư mục argocd/apps/ để tìm các app con
│   │
│   └── apps/                    ← Thư mục chứa khai báo các ứng dụng con
│       ├── web.yaml             ← Khai báo app "web" → trỏ tới k8s/web/
│       ├── frontend.yaml        ← Khai báo app "frontend" → trỏ tới k8s/frontend/
│       └── backend.yaml         ← Khai báo app "backend" → trỏ tới k8s/backend/
│
└── k8s/                         ← TÀI NGUYÊN KUBERNETES THỰC TẾ (Pod, Service, ConfigMap...)
    │
    ├── web/                     ← Tài nguyên cho ứng dụng Web (Nginx đơn giản)
    │   ├── namespace.yaml       ← Tạo namespace "demo" (nơi chứa tất cả pod)
    │   └── web.yaml             ← ConfigMap + Deployment (2 pod Nginx) + Service
    │
    ├── frontend/                ← Tài nguyên cho ứng dụng Frontend
    │   └── frontend.yaml        ← ConfigMap (chứa trang HTML + cấu hình Nginx proxy)
    │                               + Deployment (1 pod Nginx) + Service
    │
    └── backend/                 ← Tài nguyên cho ứng dụng Backend (API)
        └── backend.yaml         ← ConfigMap + Deployment (1 pod http-echo) + Service
```

### Tại sao chia thành 2 thư mục `argocd/` và `k8s/`?

| Thư mục | Vai trò | Ai đọc? |
| :--- | :--- | :--- |
| `argocd/` | Khai báo các ứng dụng cho Argo CD quản lý | **Argo CD** đọc |
| `k8s/` | Chứa tài nguyên Kubernetes thực tế (Pod, Service...) | **Kubernetes** đọc (thông qua Argo CD) |

Nói cách khác: `argocd/` là "bản đồ chỉ đường", `k8s/` là "tài nguyên thực tế cần triển khai".

---

## 3. Giải Thích Chi Tiết Từng File

### 3.1. `argocd/root.yaml` — Ứng Dụng Gốc (Root Application)

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root                    # Tên hiển thị trên giao diện Argo CD
  namespace: argocd              # Phải đặt trong namespace "argocd" (nơi Argo CD chạy)
spec:
  project: default               # Dự án mặc định của Argo CD (bắt buộc phải có)
  source:
    repoURL: https://github.com/ddor2812-dev/gitops.git   # Địa chỉ kho Git
    targetRevision: main         # Nhánh Git cần theo dõi
    path: argocd/apps            # ⭐ THƯ MỤC CẦN QUÉT — chứa các file Application con
  destination:
    server: https://kubernetes.default.svc   # Triển khai vào chính cụm K8s hiện tại
    namespace: argocd            # Các Application con sẽ được tạo trong namespace argocd
  syncPolicy:
    automated:
      prune: true                # Nếu xóa file trong Git → xóa luôn trên K8s
      selfHeal: true             # Nếu ai đó sửa tay trên K8s → Argo CD tự sửa lại theo Git
```

**Giải thích bằng ngôn ngữ đời thường:**

Root App giống như một **quản lý cấp cao**:
- Nó không tự làm việc gì cả (không tạo pod, không tạo service).
- Nó chỉ **nhìn vào thư mục `argocd/apps/`** trên GitHub.
- Mỗi file YAML trong thư mục đó là một "đơn đặt hàng" để tạo một ứng dụng con.
- Khi bạn thêm file mới vào thư mục → Root App tự động "đặt hàng" ứng dụng mới.
- Khi bạn xóa file → Root App tự động "hủy đơn" (xóa ứng dụng khỏi K8s).

---

### 3.2. `argocd/apps/web.yaml` — Khai báo ứng dụng "web"

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/ddor2812-dev/gitops.git
    targetRevision: main
    path: k8s/web               # ⭐ Trỏ tới thư mục k8s/web/ chứa tài nguyên K8s
  destination:
    server: https://kubernetes.default.svc
    namespace: demo              # Tất cả tài nguyên sẽ được tạo trong namespace "demo"
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true       # Nếu namespace "demo" chưa tồn tại → tự tạo luôn
```

**Ý nghĩa**: File này nói với Argo CD rằng: "Hãy đọc tất cả file YAML trong thư mục `k8s/web/` trên nhánh `main` của GitHub, rồi triển khai chúng vào namespace `demo`."

> `frontend.yaml` và `backend.yaml` trong `argocd/apps/` có cấu trúc tương tự, chỉ khác ở `name` và `path` (trỏ tới `k8s/frontend/` và `k8s/backend/`).

---

### 3.3. `k8s/web/namespace.yaml` — Tạo Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: demo
  annotations:
    argocd.argoproj.io/sync-wave: "-1"   # Sync wave -1 = chạy ĐẦU TIÊN trước mọi thứ
```

**Namespace** là gì? Hãy tưởng tượng namespace giống như một **phòng riêng** trong cụm Kubernetes. Các pod, service trong namespace `demo` sẽ tách biệt với các pod trong namespace khác. Bạn cần tạo "phòng" trước rồi mới đặt đồ (pod, service) vào trong được → vì vậy sync-wave là `-1` (chạy trước tiên).

---

### 3.4. `k8s/web/web.yaml` — Tài nguyên cho ứng dụng Web

File này chứa **3 tài nguyên**, ngăn cách bởi dấu `---`:

**Tài nguyên 1: ConfigMap (sync-wave: 0)**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: web-config
  namespace: demo
data:
  MESSAGE: "hello from gitops"
```
→ ConfigMap là nơi lưu trữ cấu hình dạng key-value. Ở đây nó lưu biến `MESSAGE` với giá trị `"hello from gitops"`. Deployment sẽ đọc biến này để sử dụng.

**Tài nguyên 2: Deployment (sync-wave: 1)**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2                    # Tạo 2 bản sao (pod) của ứng dụng
  selector:
    matchLabels:
      app: web                   # Deployment quản lý các pod có nhãn app=web
  template:
    metadata:
      labels:
        app: web                 # Gán nhãn app=web cho mỗi pod được tạo ra
    spec:
      containers:
      - name: web
        image: nginx:1.27        # Sử dụng image Nginx phiên bản 1.27
        envFrom:
        - configMapRef:
            name: web-config     # Đọc biến môi trường từ ConfigMap "web-config"
```
→ Deployment tạo ra 2 pod chạy Nginx. Mỗi pod đều có biến môi trường `MESSAGE=hello from gitops`.

**Tài nguyên 3: Service (sync-wave: 2)**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector:
    app: web                     # Service tìm các pod có nhãn app=web để kết nối
  ports:
  - port: 80
    targetPort: 80
```
→ Service hoạt động như một **bộ cân bằng tải nội bộ**. Khi có yêu cầu tới `web:80` trong cụm K8s, Service sẽ chuyển tiếp tới một trong 2 pod Nginx phía sau.

---

### 3.5. `k8s/backend/backend.yaml` — Tài nguyên cho Backend API

**Tài nguyên 1: ConfigMap (sync-wave: 0)**
```yaml
data:
  RESPONSE_TEXT: "Hello from Backend API"
```
→ Lưu nội dung phản hồi mà Backend sẽ trả về khi nhận được yêu cầu.

**Tài nguyên 2: Deployment (sync-wave: 1)**
```yaml
containers:
- name: backend
  image: hashicorp/http-echo:0.2.3    # Image siêu nhẹ, nhận HTTP request → trả text
  args:
  - "-text=$(RESPONSE_TEXT)"          # Trả về nội dung = giá trị biến RESPONSE_TEXT
  ports:
  - containerPort: 5678               # http-echo mặc định lắng nghe cổng 5678
```
→ `http-echo` là một container rất đơn giản: ai gửi HTTP request tới nó → nó trả về dòng text `"Hello from Backend API"`.

**Tài nguyên 3: Service (sync-wave: 2)**
```yaml
spec:
  selector:
    app: backend
  ports:
  - port: 8080              # Các pod/service khác trong K8s gọi tới backend:8080
    targetPort: 5678         # Service chuyển tiếp tới cổng 5678 của container
```
→ Bên trong cụm K8s, bất kỳ pod nào gọi tới địa chỉ `http://backend:8080` sẽ được Service chuyển tiếp tới container http-echo đang lắng nghe trên cổng 5678.

---

### 3.6. `k8s/frontend/frontend.yaml` — Tài nguyên cho Frontend

Đây là file phức tạp nhất, gồm 3 tài nguyên:

**Tài nguyên 1: ConfigMap (sync-wave: 0)** — chứa 2 file con:

- **`default.conf`** — Cấu hình Nginx:
  ```nginx
  server {
      listen 80;

      location / {
          # Khi người dùng truy cập trang chủ → trả file index.html
          root /usr/share/nginx/html;
          index index.html;
      }

      location /api/message {
          # Khi người dùng gọi /api/message → Nginx CHUYỂN TIẾP yêu cầu
          # tới service "backend" trên cổng 8080 bên trong cụm K8s
          proxy_pass http://backend:8080/;
      }
  }
  ```
  > Đây là cơ chế **Reverse Proxy**: người dùng không cần biết Backend ở đâu. Họ chỉ gọi `/api/message` tới Frontend, và Nginx tự động chuyển yêu cầu tới Backend.

- **`index.html`** — Trang giao diện web với nút bấm gọi API. Khi người dùng nhấn nút, JavaScript sẽ gọi `fetch('/api/message')` → Nginx proxy tới Backend → hiển thị kết quả.

**Tài nguyên 2: Deployment (sync-wave: 1)**
```yaml
containers:
- name: frontend
  image: nginx:1.27
  volumeMounts:
  - name: config-volume
    mountPath: /usr/share/nginx/html/index.html   # Ghi đè file index.html mặc định
    subPath: index.html
  - name: config-volume
    mountPath: /etc/nginx/conf.d/default.conf     # Ghi đè cấu hình Nginx
    subPath: default.conf
volumes:
- name: config-volume
  configMap:
    name: frontend-config     # Lấy nội dung từ ConfigMap "frontend-config"
```
→ Pod Nginx này không sử dụng trang mặc định. Thay vào đó, nó **ghi đè** bằng file HTML tùy chỉnh và cấu hình proxy từ ConfigMap.

**Tài nguyên 3: Service (sync-wave: 2)**
```yaml
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 80
```
→ Service cho phép truy cập Frontend từ bên trong cụm K8s (hoặc từ máy cá nhân qua port-forward).

---

### 3.7. `.github/workflows/validate.yml` — CI Pipeline

```yaml
name: validate
on:
  pull_request:
    paths:
      - "k8s/**"     # Chỉ kích hoạt khi PR có thay đổi file trong thư mục k8s/
```

**Mục đích**: Mỗi khi bạn tạo Pull Request (PR) có thay đổi file YAML trong thư mục `k8s/`, GitHub Actions sẽ tự động chạy công cụ `kubeconform` để kiểm tra cú pháp YAML có đúng chuẩn Kubernetes hay không — **TRƯỚC KHI** merge vào nhánh `main`.

Điều này giúp ngăn chặn lỗi cú pháp lọt vào nhánh chính và gây ra lỗi triển khai.

---

## 4. Luồng Hoạt Động Tổng Thể — Root App Quản Lý Tất Cả

Dưới đây là sơ đồ mô tả cách hệ thống hoạt động từ đầu đến cuối:

```
                         ┌─────────────────────────────────┐
                         │         GitHub Repository       │
                         │  (nhánh main)                   │
                         │                                 │
                         │  argocd/                        │
                         │    root.yaml                    │
                         │    apps/                        │
                         │      web.yaml                   │
                         │      frontend.yaml              │
                         │      backend.yaml               │
                         │                                 │
                         │  k8s/                           │
                         │    web/       (Deployment...)   │
                         │    frontend/  (Deployment...)   │
                         │    backend/   (Deployment...)   │
                         └──────────┬──────────────────────┘
                                    │
                           Argo CD quét Git
                           mỗi ~3 phút
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        CỤM KUBERNETES                                   │
│                                                                          │
│  ┌──────────────────── namespace: argocd ────────────────────────────┐   │
│  │                                                                   │   │
│  │  ┌─────────────┐                                                  │   │
│  │  │  ROOT APP   │ ← Bạn chỉ cần apply file này DUY NHẤT 1 lần    │   │
│  │  │ (root.yaml) │                                                  │   │
│  │  └──────┬──────┘                                                  │   │
│  │         │ Quét thư mục argocd/apps/ trên GitHub                   │   │
│  │         │ Tự động tạo ra 3 ứng dụng con:                         │   │
│  │         │                                                         │   │
│  │         ├──▶ Application: web      (đọc k8s/web/)                │   │
│  │         ├──▶ Application: frontend (đọc k8s/frontend/)           │   │
│  │         └──▶ Application: backend  (đọc k8s/backend/)            │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────── namespace: demo ──────────────────────────────┐   │
│  │                                                                   │   │
│  │  ┌─── App: web ───┐  ┌─ App: frontend ─┐  ┌─ App: backend ──┐  │   │
│  │  │  ConfigMap      │  │  ConfigMap       │  │  ConfigMap      │  │   │
│  │  │  Deployment x2  │  │  (HTML + Nginx)  │  │  Deployment x1 │  │   │
│  │  │  Service        │  │  Deployment x1   │  │  (http-echo)   │  │   │
│  │  │  (nginx:1.27)   │  │  Service         │  │  Service       │  │   │
│  │  └────────────────┘  └─────────────────┘  └────────────────┘  │   │
│  │                                                                   │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Quy trình từng bước:

| Bước | Điều gì xảy ra? |
| :---: | :--- |
| **1** | Bạn chạy `kubectl apply -f argocd/root.yaml` **DUY NHẤT 1 lần** để đăng ký Root App với Argo CD. |
| **2** | Root App kết nối tới GitHub, đọc thư mục `argocd/apps/`, tìm thấy 3 file: `web.yaml`, `frontend.yaml`, `backend.yaml`. |
| **3** | Root App tự động tạo ra 3 ứng dụng con trên Argo CD: `web`, `frontend`, `backend`. |
| **4** | Mỗi ứng dụng con lần lượt kết nối tới GitHub, đọc thư mục `k8s/` tương ứng của mình. |
| **5** | Các ứng dụng con tạo ra các tài nguyên Kubernetes thực tế (ConfigMap, Deployment, Service) trong namespace `demo`. |
| **6** | Kubernetes khởi tạo các Pod, các Pod bắt đầu chạy ứng dụng. |
| **7** | Từ bây giờ, mỗi khi bạn **push thay đổi lên GitHub** (nhánh `main`), Argo CD sẽ **tự động phát hiện** và cập nhật cụm K8s mà không cần bạn làm gì thêm! |

---

## 5. Sync Waves — Thứ Tự Triển Khai Tài Nguyên

Khi Argo CD đồng bộ một ứng dụng, nó không tạo tất cả tài nguyên cùng lúc. Sử dụng annotation `argocd.argoproj.io/sync-wave`, bạn kiểm soát **thứ tự triển khai**:

```
Wave -1: Namespace (tạo "phòng" trước)
   ↓
Wave  0: ConfigMap (chuẩn bị cấu hình, HTML, biến môi trường)
   ↓
Wave  1: Deployment (khởi tạo pod, pod sẽ đọc ConfigMap đã sẵn sàng)
   ↓
Wave  2: Service (mở cổng kết nối sau khi pod đã chạy ổn định)
```

**Tại sao cần thứ tự?**

Nếu Deployment được tạo trước ConfigMap → Pod sẽ khởi động nhưng không tìm thấy ConfigMap → **lỗi**.
Nếu Service được tạo trước Deployment → Service chỉ vào những pod chưa tồn tại → **trống rỗng**.

Sync Waves đảm bảo mọi thứ được tạo **đúng thứ tự, không bao giờ lỗi** do thiếu phụ thuộc.

---

## 6. Luồng Giao Tiếp Frontend ↔ Backend

Đây là luồng dữ liệu khi người dùng truy cập ứng dụng Frontend:

```
Người dùng (Browser)
    │
    │  ① Truy cập http://localhost:8080
    │     (qua kubectl port-forward)
    ▼
┌─────────────────────────┐
│   Frontend Pod (Nginx)  │
│                         │
│   Nginx nhận request:   │
│                         │
│   GET /                 │──▶ Trả file index.html (giao diện đẹp)
│                         │
│   GET /api/message      │──▶ Nginx KHÔNG trả trực tiếp
│                         │    mà CHUYỂN TIẾP (proxy_pass) tới ▼
└─────────┬───────────────┘
          │
          │  ② Nginx gọi http://backend:8080/
          │     (giao tiếp nội bộ trong cụm K8s)
          ▼
┌─────────────────────────┐
│   Backend Pod           │
│   (http-echo:0.2.3)     │
│                         │
│   Nhận request →        │
│   Trả text:             │
│   "Hello from Backend   │
│    API"                  │
└─────────┬───────────────┘
          │
          │  ③ Phản hồi quay ngược lại
          │     Backend → Nginx → Browser
          ▼
Người dùng thấy trên giao diện:
  ✅ "Hello from Backend API" (màu xanh lá)
```

### Tại sao dùng Nginx Proxy thay vì gọi Backend trực tiếp?

1. **Bảo mật**: Backend chỉ mở cổng bên trong cụm K8s, không ai từ bên ngoài truy cập được trực tiếp.
2. **Tránh lỗi CORS**: Browser không cho phép gọi API sang domain/port khác (Cross-Origin). Nhưng nếu Frontend và API cùng domain (nhờ proxy), thì không có vấn đề gì.
3. **Đơn giản**: Người dùng chỉ cần biết 1 địa chỉ duy nhất (Frontend), không cần biết Backend ở đâu.

---

## 7. CI Pipeline — Kiểm Tra Tự Động Khi Tạo Pull Request

```
Developer sửa file trong k8s/ → Tạo PR vào nhánh main
                │
                ▼
┌──────────────────────────────────┐
│ GitHub Actions tự động chạy:     │
│                                  │
│ 1. Tải công cụ kubeconform       │
│ 2. Chạy: kubeconform -strict k8s/│
│                                  │
│ Kết quả:                         │
│   ✅ Pass → PR có thể merge      │
│   ❌ Fail → PR bị chặn           │
│      (file YAML sai cú pháp)     │
└──────────────────────────────────┘
```

**Ý nghĩa**: Trước khi code được merge vào nhánh `main` (và được Argo CD triển khai lên K8s), hệ thống CI sẽ kiểm tra xem các file YAML có đúng chuẩn Kubernetes không. Nếu sai → **chặn merge**, tránh gây lỗi trên môi trường thật.

---

## 8. Hướng Dẫn Triển Khai Từng Bước

### Điều kiện cần có
- Một cụm Kubernetes đang chạy (minikube, kind, hoặc trên cloud).
- Argo CD đã được cài đặt trong cụm (namespace `argocd` phải tồn tại).
- `kubectl` đã được kết nối tới cụm.

### Bước 1: Đăng ký Root App (chỉ cần làm 1 lần duy nhất)

```bash
kubectl apply -f argocd/root.yaml
```

Lệnh này tạo ứng dụng `root` trên Argo CD. Từ đây, Argo CD sẽ tự quản lý mọi thứ.

### Bước 2: Đẩy code lên GitHub (nếu chưa push)

```bash
git add .
git commit -m "feat: restructure k8s and implement frontend-backend"
git push origin main
```

### Bước 3: Chờ Argo CD đồng bộ

Argo CD quét Git mỗi ~3 phút. Nếu muốn nhanh hơn:
- Mở **Argo CD UI** → click vào ứng dụng `root` → nhấn nút **Refresh**.
- Hoặc chạy lệnh:
  ```bash
  kubectl annotate application root -n argocd argocd.argoproj.io/refresh=normal --overwrite
  ```

### Bước 4: Kiểm tra trạng thái

```bash
# Xem tất cả ứng dụng Argo CD
kubectl get application -n argocd

# Kết quả mong đợi:
# NAME       SYNC STATUS   HEALTH STATUS
# root       Synced        Healthy
# web        Synced        Healthy
# frontend   Synced        Healthy
# backend    Synced        Healthy
```

```bash
# Xem tất cả tài nguyên trong namespace demo
kubectl get all -n demo

# Kết quả mong đợi: các pod frontend, backend, web đều Running
```

### Bước 5: Truy cập ứng dụng Frontend

```bash
# Tạo đường hầm từ máy cá nhân tới service frontend trong K8s
kubectl port-forward svc/frontend -n demo 8080:80
```

Mở trình duyệt: [http://localhost:8080](http://localhost:8080)

Bạn sẽ thấy:
1. Giao diện **GitOps Workspace** nền tối, thiết kế hiện đại.
2. Nhấn nút **"Gửi yêu cầu tới Backend API"**.
3. Nếu thành công → hiện chữ `Hello from Backend API` màu xanh lá ✅

### Bước 6 (tùy chọn): Thêm ứng dụng mới trong tương lai

Muốn thêm ứng dụng mới (ví dụ: `monitoring`)? Rất đơn giản:

1. Tạo thư mục `k8s/monitoring/` chứa file YAML cho Deployment, Service...
2. Tạo file `argocd/apps/monitoring.yaml` trỏ tới `k8s/monitoring/`.
3. Push lên GitHub.
4. Root App sẽ **tự động phát hiện** và triển khai — bạn không cần chạy lệnh gì thêm!

Đây chính là sức mạnh của mô hình **App-of-Apps + GitOps** 🚀
