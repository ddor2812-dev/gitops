# Hướng Dẫn Thực Hành: 4 Bài Lab Nâng Cao với GitOps & Kubernetes

Tài liệu này hướng dẫn chi tiết cách thực hiện 4 bài Lab nâng cao tiếp nối dự án GitOps App-of-Apps hiện tại. Chúng ta sẽ tích hợp hệ thống giám sát (Prometheus & Grafana), bộ điều khiển triển khai nâng cao (Argo Rollouts), và thực hiện chiến lược phát hành Canary cho ứng dụng Flask API.

---

## Mục Lục

1. [Giải thích các khái niệm nâng cao](#1-giải-thích-các-khái-niệm-nâng-cao)
2. [Tổng quan luồng hoạt động](#2-tổng-quan-luồng-hoạt-động)
3. [Chi tiết từng bài Lab và các bước thực hiện](#3-chi-tiết-từng-bài-lab-và-các-bước-thực-hiện)
   - [Lab 1: Cài đặt Prometheus Stack & Argo Rollouts qua GitOps](#lab-1-cài-đặt-prometheus-stack--argo-rollouts-qua-gitops)
   - [Lab 2: Xây dựng và Docker hóa Flask API có Metrics](#lab-2-xây-dựng-và-docker-hóa-flask-api-có-metrics)
   - [Lab 3: Triển khai Canary Rollout & Cấu hình ServiceMonitor](#lab-3-triển-khai-canary-rollout--cấu-hình-servicemonitor)
   - [Lab 4: Thực hiện Canary Deployment & Giám sát trực quan](#lab-4-thực-hiện-canary-deployment--giám-sát-trực-quan)
4. [Giải thích chi tiết các File cấu hình](#4-giải-thích-chi-tiết-các-file-cấu-hình)

---

## 1. Giải Thích Các Khái Niệm Nâng Cao

### Prometheus & Grafana là gì?
*   **Prometheus** là hệ thống giám sát và cảnh báo mã nguồn mở. Nó hoạt động theo cơ chế **Pull**, tức là định kỳ đi "quét" (scrape) các endpoint `/metrics` của ứng dụng để thu thập các thông số như số lượng request, thời gian xử lý, số lỗi 500...
*   **Grafana** là công cụ trực quan hóa dữ liệu. Nó kết nối tới Prometheus để vẽ các biểu đồ đẹp mắt (Dashboard), giúp bạn theo dõi sức khỏe hệ thống trực quan hơn.

### ServiceMonitor là gì?
Thông thường để Prometheus biết cần thu thập metric từ service nào, bạn phải cấu hình thủ công trong file Prometheus config.
Trong Kubernetes sử dụng **Prometheus Operator**, bạn chỉ cần tạo một tài nguyên gọi là **ServiceMonitor**. Prometheus Operator sẽ tự động phát hiện ServiceMonitor này và bảo Prometheus đi scrape Service tương ứng.

### Argo Rollouts là gì?
Deployment mặc định của Kubernetes chỉ hỗ trợ chiến lược cập nhật **RollingUpdate** (thay thế dần pod cũ bằng pod mới). Chiến lược này khá rủi ro vì nếu pod mới có lỗi logic ẩn, hệ thống vẫn sẽ thay thế 100% pod cũ.
**Argo Rollouts** là một Kubernetes Controller cung cấp các chiến lược triển khai nâng cao như **Blue-Green** và **Canary**.

### Chiến lược Canary là gì?
Canary là chiến lược phát hành phiên bản mới (`v2`) bằng cách chuyển một **tỷ lệ phần trăm nhỏ lưu lượng truy cập** (ví dụ 25%) sang phiên bản mới, trong khi phần lớn người dùng vẫn dùng bản cũ (`v1`).
Sau một thời gian kiểm tra (qua Prometheus hoặc kiểm tra thủ công), nếu phiên bản mới hoạt động tốt, bạn sẽ tăng tỷ lệ lên 50%, 100% để hoàn tất phát hành. Nếu phát hiện lỗi, bạn có thể **Rollback ngay lập tức** mà không ảnh hưởng tới 75% người dùng còn lại.

---

## 2. Tổng Quan Luồng Hoạt Động

Dưới đây là sơ đồ luồng hoạt động khi triển khai ứng dụng API và cấu hình giám sát:

```
                                      ┌────────────────┐
                                      │   Prometheus   │
                                      └───────┬────────┘
                                              │
                              ① Scrape metrics mỗi 15 giây
                              (thông qua ServiceMonitor)
                                              │
                                              ▼
┌───────────────────────────────── namespace: demo ──────────────────────────────────┐
│                                                                                    │
│                           ┌────────── Service: api ──────────┐                     │
│                           │            (Port 8080)           │                     │
│                           └─────────────────┬────────────────┘                     │
│                                             │                                      │
│                  ┌──────────────────────────┴──────────────────────────┐           │
│                  │ (Điều hướng traffic theo tỷ lệ Canary)               │           │
│                  ▼                                                     ▼           │
│    ┌───────────────────────────┐                         ┌───────────────────────────┐     │
│    │      Pods Phiên bản v1     │                         │      Pods Phiên bản v2     │     │
│    │         (75% Traffic)     │                         │         (25% Traffic)     │     │
│    │  - w9-api:1               │                         │  - w9-api:2               │     │
│    │  - Phục vụ ổn định        │                         │  - Đang thử nghiệm        │     │
│    └───────────────────────────┘                         └───────────────────────────┘     │
│                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Chi Tiết Từng Bài Lab và Các Bước Thực Hiện

### Lab 1: Cài đặt Prometheus Stack & Argo Rollouts qua GitOps

Trong mô hình App-of-Apps, chúng ta không dùng lệnh `helm install` thủ công. Thay vào đó, ta khai báo các file Application Helm và đẩy lên Git để Root App tự động cài đặt.

**Các bước thực hiện:**
1.  Đẩy file cấu hình [kube-prometheus-stack.yaml](file:///Users/nguyenphutai/gitops/gitops/argocd/apps/kube-prometheus-stack.yaml) và [argo-rollouts.yaml](file:///Users/nguyenphutai/gitops/gitops/argocd/apps/argo-rollouts.yaml) vào thư mục `argocd/apps/`.
2.  Thực hiện Git commit và push lên nhánh `main`.
3.  Root App sẽ tự động quét thấy và tạo ra 2 ứng dụng mới trên Argo CD UI.
4.  Đợi vài phút để các Pod trong namespace `monitoring` và `argo-rollouts` khởi chạy thành công.

---

### Lab 2: Xây dựng và Docker hóa Flask API có Metrics

Chúng ta xây dựng một API đơn giản bằng Flask (Python). API này xuất ra các metric ở định dạng Prometheus trên đường dẫn `/metrics` và hỗ trợ cấu hình tỉ lệ lỗi giả lập để phục vụ kiểm tra Canary.

**Các bước thực hiện:**
1.  Ứng dụng Flask nằm ở thư mục `app/app.py`.
2.  Dockerfile nằm ở thư mục `app/Dockerfile`.
3.  Tạo Docker image cục bộ và nạp trực tiếp vào cụm Minikube `w9`:
    ```bash
    # Build image cục bộ
    docker build -t w9-api:1 app/
    
    # Nạp image vào trong cụm minikube
    minikube -p w9 image load w9-api:1
    ```

---

### Lab 3: Triển khai Canary Rollout & Cấu hình ServiceMonitor

Chúng ta sẽ khai báo tài nguyên dạng `Rollout` thay thế cho `Deployment` để Argo Rollouts quản lý quá trình cập nhật Canary.

**Các bước thực hiện:**
1.  Đẩy cấu hình ứng dụng API và ServiceMonitor vào thư mục `k8s-api/` (`api.yaml` và `servicemonitor.yaml`).
2.  Đăng ký ứng dụng `api` với Argo CD bằng cách thêm file khai báo ứng dụng [api.yaml](file:///Users/nguyenphutai/gitops/gitops/argocd/apps/api.yaml) vào `argocd/apps/`.
3.  Commit và push lên Git.
4.  Kiểm tra trên Argo CD để đảm bảo ứng dụng `api` đã được tạo và đồng bộ thành công.
5.  Kiểm tra xem các Pod chạy API đã hoạt động chưa:
    ```bash
    kubectl get pods -n demo -l app=api
    ```

---

### Lab 4: Thực hiện Canary Deployment & Giám sát trực quan

Bài lab này kiểm chứng sức mạnh của Argo Rollouts khi nâng cấp ứng dụng từ phiên bản `v1` lên `v2`.

**Các bước thực hiện:**

#### Bước 4.1: Kiểm tra kết nối và Metric hiện tại
1.  Tạo đường hầm port-forward để truy cập Prometheus UI:
    ```bash
    kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9090:9090
    ```
    Mở trình duyệt: **http://localhost:9090**, chuyển sang tab **Status -> Targets**. Kiểm tra xem target `demo/api-monitor` đã ở trạng thái **UP** chưa.
2.  Thực hiện một vài request tới API để sinh dữ liệu:
    ```bash
    # Port forward tới API service
    kubectl port-forward svc/api -n demo 8085:8080
    
    # Chạy curl liên tục hoặc truy cập trình duyệt http://localhost:8085
    curl http://localhost:8085/
    ```
3.  Vào Prometheus UI, gõ query: `flask_http_request_total` và nhấn **Execute** để xem số lượng request đã được ghi nhận.

#### Bước 4.2: Triển khai Canary phiên bản v2
1.  Mở file [k8s-api/api.yaml](file:///Users/nguyenphutai/gitops/gitops/k8s-api/api.yaml).
2.  Thay đổi giá trị biến môi trường `VERSION` từ `"v1"` thành `"v2"`.
3.  Chạy lệnh theo dõi trạng thái Rollout trong một terminal khác:
    ```bash
    kubectl argo rollouts get rollout api -n demo --watch
    ```
4.  Commit và push thay đổi YAML lên Git:
    ```bash
    git add k8s-api/api.yaml && git commit -m "upgrade: api to v2" && git push origin main
    ```
5.  Sau khi Argo CD đồng bộ, bạn sẽ quan sát thấy trên màn hình CLI Rollout:
    *   Argo Rollouts tạo ra 1 pod `v2` (tương ứng với 25% trọng số của tổng số 4 replicas).
    *   3 pod còn lại vẫn là `v1` (75%).
    *   Quá trình rollout rơi vào trạng thái **Paused** vô thời hạn do cấu hình `pause: {}` ở bước đầu tiên.

#### Bước 4.3: Kiểm tra điều hướng traffic và Quyết định (Promote hoặc Abort)
1.  Gửi liên tiếp các yêu cầu tới API thông qua lệnh:
    ```bash
    while true; do curl -s http://localhost:8085/ | grep version; sleep 0.5; done
    ```
    Bạn sẽ thấy khoảng 25% kết quả trả về chữ `"v2"` và 75% trả về chữ `"v1"`.
2.  **Kịch bản 1: Mọi thứ chạy tốt -> Promote lên 100%**
    Nếu bạn hài lòng với phiên bản mới, chạy lệnh sau để tiếp tục rollout:
    ```bash
    kubectl argo rollouts promote api -n demo
    ```
    Rollout sẽ tự động tăng tỷ lệ lên 50% -> đợi 30 giây -> và tự động tăng lên 100% hoàn thành phát hành.
3.  **Kịch bản 2: Phát hiện lỗi -> Abort (Rollback ngay lập tức)**
    Nếu bạn phát hiện lỗi logic ở phiên bản `v2`, bạn có thể thu hồi ngay lập tức để bảo vệ người dùng bằng lệnh:
    ```bash
    kubectl argo rollouts abort api -n demo
    ```
    Argo Rollouts sẽ lập tức ngắt toàn bộ traffic khỏi các Pod `v2` và đưa hệ thống về trạng thái `v1` an toàn 100%.

---

## 4. Giải Thích Chi Tiết Các File Cấu Hình

### 4.1. File `argocd/apps/kube-prometheus-stack.yaml`
```yaml
spec:
  source:
    chart: kube-prometheus-stack
    repoURL: https://prometheus-community.github.io/helm-charts
    targetRevision: 65.1.1 # Phiên bản helm chart của Prometheus stack
    helm:
      values: |
        grafana:
          adminPassword: admin # Đặt mật khẩu đăng nhập Grafana mặc định là 'admin'
        prometheus:
          prometheusSpec:
            # Rất quan trọng! Cho phép Prometheus thu thập metric từ mọi ServiceMonitor 
            # mà không bị bắt buộc phải trùng label của Prometheus Helm release.
            serviceMonitorSelectorNilUsesHelmValues: false 
```

### 4.2. File `k8s-api/api.yaml` (Phần Rollout)
```yaml
kind: Rollout # Sử dụng tài nguyên Rollout của Argo
spec:
  replicas: 4 # Tổng số Pod chạy ứng dụng
  strategy:
    canary:
      steps:
      - setWeight: 25 # Bước 1: Cho 25% traffic (tương đương 1 Pod) chạy bản v2
      - pause: {}     # Bước 2: Tạm dừng vô hạn để kiểm thử thủ công/chờ promote
      - setWeight: 50 # Bước 3: Nếu promote, tăng lên 50% traffic (2 Pod v2, 2 Pod v1)
      - pause:
          duration: 30s # Bước 4: Tự động chờ 30 giây, nếu không có lỗi sẽ tự động lên 100%

---

## 5. Phụ Lục: Xử lý lỗi phổ biến khi cài đặt Prometheus Stack (Too long annotations)

### Mô tả lỗi
Khi Argo CD đồng bộ Helm Chart `kube-prometheus-stack`, bạn có thể thấy ứng dụng bị kẹt ở trạng thái **OutOfSync** với thông báo lỗi:
`CustomResourceDefinition.apiextensions.k8s.io "thanosrulers.monitoring.coreos.com" is invalid: metadata.annotations: Too long: may not be more than 262144 bytes`

**Nguyên nhân**: Theo mặc định, `kubectl apply` lưu cấu hình cũ vào trường annotation `kubectl.kubernetes.io/last-applied-configuration`. Do các file định nghĩa CRD của Prometheus quá lớn, dung lượng này vượt quá giới hạn 256KB của Kubernetes.

### Cách khắc phục từng bước:

#### Bước 1: Cấu hình Server-Side Apply
Chúng ta thêm `ServerSideApply=true` vào danh sách `syncOptions` của Application trên Argo CD. Điều này yêu cầu Kubernetes thực hiện ghép cấu hình trên máy chủ mà không tạo annotation dung lượng lớn.
*(Tôi đã cập nhật cấu hình này trong file `argocd/apps/kube-prometheus-stack.yaml` và đẩy lên Git)*.

#### Bước 2: Dừng tiến trình Retry bị kẹt trên Argo CD
Do Argo CD tự động thử lại (retry) lệnh đồng bộ cũ bị lỗi, ta cần xóa trạng thái chạy dở dang này bằng lệnh:
```bash
kubectl patch application kube-prometheus-stack -n argocd --type json -p '[{"op": "remove", "path": "/operation"}]'
```

#### Bước 3: Cài đặt thủ công các CRD lớn bằng Server-Side Apply
Nếu Argo CD vẫn gặp khó khăn trong việc khởi tạo các CRD này lần đầu, bạn hãy chạy trực tiếp các lệnh dưới đây để nạp chúng từ kho chính thức của Prometheus Operator:
```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagerconfigs.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_alertmanagers.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheusagents.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_prometheuses.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_scrapeconfigs.yaml
kubectl apply --server-side -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/v0.74.0/example/prometheus-operator-crd/monitoring.coreos.com_thanosrulers.yaml
```

#### Bước 4: Yêu cầu Argo CD đồng bộ lại
Sau khi nạp xong CRD, bạn ra lệnh cho Argo CD đồng bộ lại để kéo các tài nguyên còn lại:
```bash
kubectl annotate application kube-prometheus-stack -n argocd argocd.argoproj.io/refresh=hard --overwrite
```

```
