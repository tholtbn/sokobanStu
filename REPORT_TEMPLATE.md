# Mô tả thiết kế solver Sokoban

<<<<<<< HEAD
Tài liệu này dùng để giải thích bài nộp, không có điểm riêng trong thang chấm.
Không bắt buộc một thuật toán, heuristic hay cấu trúc dữ liệu cụ thể.

## 1. Thiết kế
Mô tả phương pháp giải, cách tổ chức chương trình và lý do lựa chọn.

## 2. Chất lượng lời giải
Giải thích phương pháp tìm hoặc cải thiện lời giải. Nếu tuyên bố tối ưu,
trình bày cơ sở cho tuyên bố đó; nếu không, nêu rõ giới hạn.

## 3. Thực nghiệm
Ghi các map đã thử, có giải được hay không và số bước của lời giải.
Có thể ghi thêm thời gian để phân tích, dù thời gian không trực tiếp tính điểm.

## 4. Hạn chế và nguồn tham khảo
Nêu phần chưa hoàn thiện, tài liệu, mã nguồn và công cụ AI đã sử dụng.
=======
## 1. Thiết kế

**Phương pháp.** Tìm kiếm cấp "lần đẩy" (macro-push) bằng weighted A* kiểu anytime.
Một nước đi = chọn robot *i*, đi bộ (BFS, coi hộp và robot khác là vật cản) tới ô ngay
sau hộp rồi đẩy hộp một ô. Chi phí = số bước đi + 1, nên tổng chi phí đúng bằng số bước
theo luật (đi bộ và đẩy đều tính một bước).

**Tổ chức chương trình** (toàn bộ trong `solution.py`, chỉ dùng thư viện chuẩn):

| Thành phần | Vai trò |
|---|---|
| `_Board` | Tiền xử lý một lần: bảng láng giềng, khoảng cách đẩy ngược từ mỗi đích, ô chết, heuristic, kiểm tra freeze-deadlock |
| `_Solver.macro` | Weighted A* trên các lần đẩy, kèm "nước né" cho robot đang chặn |
| `_Solver.primitive` | A* từng bước chính xác (tinh chỉnh / dự phòng) |
| `_replay` | Phát lại đường đi bằng `state.successors()` của framework |
| `solve` | Điều phối các giai đoạn, kiểm soát thời gian, không bao giờ ném ngoại lệ |

**Các quyết định chính và lý do**
- *Gộp bước đi bộ vào macro*: thu nhỏ mạnh không gian trạng thái mà vẫn đếm đủ chi phí.
- *Heuristic chấp nhận được*: (a) khoảng cách đẩy ngược (BFS ngược đúng luật: cần ô trống
  cho cả hộp lẫn robot), (b) ghép cặp hộp-đích tối ưu bằng thuật toán Hungary (cache theo
  cấu hình hộp), (c) cận dưới số bước đi bộ tới lần đẩy đầu tiên.
- *Cắt tỉa an toàn*: ô chết và freeze-deadlock (thùng bị đóng băng không ở đích).
- *Gộp đối xứng robot*: các robot như nhau nên khóa trạng thái dùng vị trí robot đã sắp xếp.
- *Nước né*: robot đang chặn một lần đẩy hợp lệ được phép bước sang ô trống (không đẩy).
- *Dựng lại đường đi qua `successors()`*: chuỗi `parent / action / gval` luôn hợp lệ theo
  đúng luật của framework, không tự tạo trạng thái.
- *Không sửa `initial_state`*: chỉ đọc dữ liệu, mọi trạng thái mới do `successors()` tạo ra.

**Luồng `solve`:** (0) đã ở đích → trả chính trạng thái đó; `timebound <= 0` → `False`.
(1) macro anytime, trọng số 4 → 2 → 1.4 → 1.15 → 1 (có trọng số trung gian khi chạm trần
bộ nhớ). (2) A* từng bước chính xác với cận trên là lời giải macro. Hết giờ mà chưa có
lời giải → `False`. Thời gian sử dụng ≈ 88% `timebound`.

## 2. Chất lượng lời giải

- Mỗi vòng weighted A* dùng lời giải tốt nhất làm cận trên và cắt các nút có `g + h ≥ cận`
  (h chấp nhận được nên không mất lời giải tốt hơn). Các vòng sau cải thiện dần.
- **Tuyên bố tối ưu chỉ khi có cơ sở**: A* từng bước với w = 1 chạy cạn (hoặc tìm ra
  nghiệm ở w = 1) với heuristic chấp nhận được và cắt tỉa an toàn ⇒ nghiệm tối ưu.
  Solver ghi cờ này vào `solution._LAST_INFO`.
- Kiểm chứng độc lập: so với BFS vét cạn chỉ dùng framework trên ~390 map ngẫu nhiên nhỏ
  giải được (5 seed): **tất cả đều tối ưu**; mọi map vô nghiệm đều trả `False`.
- **Giới hạn**: mô hình macro không biểu diễn được "robot đi trước chiếm chỗ" (xem mục 4);
  giai đoạn A* từng bước vá điều này nhưng chỉ chạy xong ở map nhỏ. Với map lớn, kết quả
  là lời giải tốt nhất trong thời gian cho phép, **không tuyên bố tối ưu**.

## 3. Thực nghiệm (20 map thực hành; hợp lệ kiểm bằng `validation.py`)

Máy 1 lõi, mỗi map một tiến trình. Map 0–8, 12–14 đo ở ngân sách 30s; map 9–11 và 15–19 đo ở 120s.

| Map | Bước | Trạng thái | Thời gian |
|---|---|---|---|
| 0 | 16 | Tối ưu (chứng minh) | 0.2s |
| 1 | 4 | Tối ưu | <0.01s |
| 2 | 21 | Tối ưu | 0.02s |
| 3 | 10 | Tối ưu | 0.01s |
| 4 | 8 | Tối ưu | <0.01s |
| 5 | 30 | Tối ưu | 0.4s |
| 6 | 16 | Tối ưu | 0.01s |
| 7 | 41 | Tối ưu | 0.01s |
| 8 | 14 | Tối ưu | 0.4s |
| 9 | 24 | Chưa chứng minh | ~106s |
| 10 | 31 | Chưa chứng minh | ~47s |
| 11 | 26 | Tối ưu (chứng minh) | 31s |
| 12 | 24 | Tối ưu | 12s |
| 13 | 27 | Tối ưu | 5s |
| 14 | 25 | Tối ưu | 3s |
| 15 | 68 | Chưa chứng minh | 23s |
| 16 | 56 | Chưa chứng minh | 21s |
| 17 | 92 | Chưa chứng minh | 24s |
| 18 | 93 | Chưa chứng minh | 37s |
| 19 | 76 | Chưa chứng minh | 37s |

20/20 map giải được. Bộ test framework và `autograder.py` đều qua. Bộ nhớ đỉnh khoảng
150–435 MB trên các map khó.
Bản `solution.py` có sẵn trong repo (trước khi sửa) chỉ giải được 2/20 map do lỗi tính ô chết.

## 4. Hạn chế và nguồn tham khảo

**Hạn chế**
- Mô hình macro không biểu diễn được trường hợp robot phải đi trước chiếm vị trí trước
  khi hộp đóng mất đường; chỉ giai đoạn A* từng bước (map nhỏ) mới bù được.
- Map 8×8 (15–19): heuristic còn lỏng (ví dụ map 17: h gốc 49, lời giải 92), vì chưa tính
  đủ bước đi bộ ⇒ không thể chứng minh tối ưu; thêm thời gian vẫn còn cải thiện được
  (map 19: 83 bước ở 30s → 76 bước ở 120s).
- Bộ nhớ: trần 700k nút/vòng (`NODE_CAP`) cho mức đỉnh ~435 MB; hạ hằng số này nếu môi
  chấm giới hạn bộ nhớ chặt hơn.
- Solver có thể dừng sớm (~20–40s) trên map lớn khi mọi vòng đã chạm trần bộ nhớ.
- Chưa đo trên bộ test ẩn; thời gian đo trên máy 1 lõi có thể khác môi trường chấm.

**Nguồn / công cụ.** Thuật toán Hungary (Kuhn–Munkres, biến thể có thế năng);
weighted A* và restarting weighted A* (anytime search); khái niệm ô chết và freeze
deadlock trong các solver Sokoban. Mã nguồn tự viết dựa trên framework được cung cấp.
Công cụ AI sử dụng: Claude (Anthropic), hỗ trợ thiết kế, viết mã, kiểm thử.
>>>>>>> 777327d (Update project)
