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

### Lab 4: Thực Hiện Canary Tự Động Hóa & Đo Lường Cảnh Báo (SLO/Alert)

Bài lab này kiểm chứng khả năng tự động hóa 100% của hệ thống GitOps & Progressive Delivery. Chúng ta sẽ nâng cấp API lên bản mới, để hệ thống tự đo lường thông số (Observability), tự đưa ra quyết định nâng cấp hoặc tự động rút lui (Auto-abort & Rollback) nếu chất lượng không đạt SLO (Success Rate >= 95%).

---

#### Bước 4.1: Kiểm tra kết nối và cấu hình Alerts
1.  **Mở Port-forward tới các dịch vụ:**
    *   API Service (Port 8085):
        ```bash
        kubectl port-forward svc/api -n demo 8085:8080
        ```
    *   Prometheus UI (Port 9095):
        ```bash
        kubectl port-forward svc/kube-prometheus-stack-prometheus -n monitoring 9095:9090
        ```
    *   Alertmanager UI (Port 9093):
        ```bash
        kubectl port-forward svc/kube-prometheus-stack-alertmanager -n monitoring 9093:9093
        ```
2.  **Theo dõi trạng thái Rollout trực quan qua CLI:**
    Mở một cửa sổ terminal riêng biệt và chạy lệnh theo dõi:
    ```bash
    kubectl argo rollouts get rollout api -n demo --watch
    ```

---

#### Bước 4.2: Kịch bản 1 — Nâng cấp Thành công (Bản tốt -> 100% tự động)
1.  Mở file `k8s-api/api.yaml`, sửa giá trị biến môi trường `VERSION` từ `"v1"` thành `"v2"`. Giữ nguyên `ERROR_RATE` bằng `"0"`.
2.  Commit và push lên Git:
    ```bash
    git add k8s-api/api.yaml && git commit -m "upgrade: api to v2" && git push origin main
    ```
3.  **Quan sát:**
    *   Argo CD tự động đồng bộ và Argo Rollouts bắt đầu tạo Pod `v2` (tỷ lệ 25%).
    *   Một tài nguyên `AnalysisRun` sẽ tự động được sinh ra trong nền và bắt đầu truy vấn Prometheus mỗi 10 giây để kiểm tra tỷ lệ thành công của API.
    *   Sau 20 giây ở bước 25% và 20 giây ở bước 50%, do tỷ lệ thành công đạt 100% (luôn >= 95%), hệ thống sẽ tự động chuyển sang tỷ lệ 100% thành công tốt đẹp!

---

#### Bước 4.3: Kịch bản 2 — Bản lỗi tự động Hủy bỏ (Auto-abort & Auto-rollback)
Bây giờ, chúng ta sẽ giả lập một lỗi nghiêm trọng ở phiên bản `v3` để kiểm thử hệ thống tự bảo vệ.
1.  Mở file `k8s-api/api.yaml`, sửa `VERSION` thành `"v3"` và đặt `ERROR_RATE` thành `"0.2"` (giả lập 20% yêu cầu sẽ bị lỗi HTTP 500).
2.  Commit và push lên Git:
    ```bash
    git add k8s-api/api.yaml && git commit -m "upgrade: api to v3 with error simulation" && git push origin main
    ```
3.  **Kích hoạt sinh dữ liệu (Traffic generator):**
    Chạy lệnh gửi request liên tục trong terminal để tạo metric lỗi cho Prometheus:
    ```bash
    while true; do curl -s http://localhost:8085/ | grep version; sleep 0.2; done
    ```
4.  **Quan sát hệ thống tự bảo vệ:**
    *   **Tự động Hủy bỏ (Auto-abort):** Trên giao diện theo dõi `kubectl argo rollouts`, khi traffic lỗi đạt 20%, Prometheus ghi nhận tỷ lệ thành công chỉ đạt ~80% (dưới ngưỡng 95% của SLO). Sau 3 lần đo liên tiếp bị lỗi, Argo Rollouts sẽ chuyển trạng thái của Rollout từ `Progressing` thành **`Degraded (Aborted)`** và ngay lập tức thu hồi bản `v3`, đưa traffic quay về 100% bản `v2` an toàn!
    *   **Alert kích hoạt gửi Email:** Vào giao diện Alertmanager (**http://localhost:9093**), bạn sẽ thấy cảnh báo **`ApiHighErrorRate`** chuyển sang màu đỏ kích hoạt (**Firing**). Alertmanager sẽ kích hoạt luồng gửi mail SMTP đến hộp thư `ddor2812@gmail.com` của bạn để báo cáo chất lượng dịch vụ sụt giảm.

---

#### Bước 4.4: Kịch bản 3 — Rollback thủ công qua Git cực nhanh (< 5 phút)
Nếu bạn lỡ push một thay đổi bị lỗi lên Git và muốn khôi phục an toàn:
1.  Chạy lệnh khôi phục Git commit trước đó:
    ```bash
    git revert HEAD --no-edit
    ```
2.  Push code lên nhánh chính:
    ```bash
    git push origin main
    ```
3.  Argo CD sẽ tự động phát hiện thay đổi và đồng bộ cụm K8s về đúng trạng thái an toàn trên Git. Toàn bộ quy trình diễn ra hoàn toàn tự động chỉ trong vòng chưa đầy 2 phút, đảm bảo tính nhất quán (no drift) giữa Git và hệ thống thực tế!

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

### 4.2. File `k8s-api/api.yaml` (Phần Rollout và Service)
```yaml
strategy:
  canary:
    analysis:
      templates:
      - templateName: success-rate # Liên kết với AnalysisTemplate đo lường tự động
    steps:
    - setWeight: 25
    - pause:
        duration: 20s # Tạm dừng 20s để AnalysisRun thu thập đủ metric đánh giá
    - setWeight: 50
    - pause:
        duration: 20s # Tiếp tục giám sát 20s trước khi lên 100%
```

### 4.3. File `k8s-api/analysistemplate.yaml`
```yaml
spec:
  metrics:
  - name: success-rate
    interval: 10s # Đo lường mỗi 10 giây
    successCondition: result[0] >= 0.95 # SLO tỷ lệ thành công >= 95%
    failureLimit: 3 # Cho phép tối đa 3 lần lỗi liên tiếp trước khi rollback
    provider:
      prometheus:
        address: http://kube-prometheus-stack-prometheus.monitoring.svc:9090
        query: |
          sum(rate(flask_http_request_total{status!~"5.*",job="api",namespace="demo"}[1m]))
          /
          sum(rate(flask_http_request_total{job="api",namespace="demo"}[1m])) or vector(1)
```

### 4.4. File `k8s-api/prometheusrule.yaml`
```yaml
spec:
  groups:
  - name: api.rules
    rules:
    - alert: ApiHighErrorRate # Định nghĩa tên Alert
      expr: |
        # Kích hoạt alert nếu tỷ lệ lỗi HTTP 5xx vượt quá 5%
        (sum(rate(flask_http_request_total{status=~"5..",job="api",namespace="demo"}[1m]))
        /
        sum(rate(flask_http_request_total{job="api",namespace="demo"}[1m])) or vector(0)) > 0.05
      for: 10s # Chỉ kích hoạt nếu lỗi liên tục kéo dài trên 10 giây
      labels:
        severity: critical
```

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
