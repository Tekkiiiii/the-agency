# Ví dụ chọn lọc

## Cần sửa

Input: "Giải pháp này đóng vai trò quan trọng trong việc giúp nhóm nâng cao hiệu suất."

Output: "Giải pháp này giúp nhóm làm việc nhanh hơn."

Chỉ dùng output nếu "hiệu suất" trong ngữ cảnh thực sự là tốc độ. Nếu hiệu suất còn gồm chi phí hoặc độ chính xác, giữ nghĩa rộng hơn.

Input: "Trong bài viết này, chúng ta sẽ cùng tìm hiểu cách bộ nhớ đệm giảm số lần ứng dụng phải đọc lại cùng một dữ liệu."

Output: "Bộ nhớ đệm giảm số lần ứng dụng phải đọc lại cùng một dữ liệu."

Input: "Trong bối cảnh kỷ nguyên số không ngừng phát triển, doanh nghiệp cần đổi mới."

Output: "Doanh nghiệp cần đổi mới." Chỉ thay bằng một thay đổi cụ thể nếu input hoặc context thực sự cung cấp thay đổi đó.

Input (blog, VI-HUM-L08): "Trong thời đại ngày nay, doanh nghiệp nhỏ cần một kênh bán hàng trực tuyến."

Output: "Doanh nghiệp nhỏ cần một kênh bán hàng trực tuyến."

Lời dẫn khuôn không nêu mốc thời gian hay thay đổi nào nên bỏ được. Giữ nguyên "cần", không nâng thành "phải"; nếu câu ngay sau có số liệu làm lời dẫn có nội dung thì L08 không áp dụng.

Input (kỹ thuật, VI-HUM-D04): "Như đã đề cập ở trên, bộ nhớ đệm giảm số lần truy cập nguồn. Dưới đây là ba cách cấu hình."

Output: "Bộ nhớ đệm giảm số lần truy cập nguồn, và có ba cách cấu hình."

Hai nhãn điều hướng liền nhau lặp lại việc mà heading đã làm. Giữ nguyên con số ba và thuật ngữ; trong runbook hay tài liệu dài cần dẫn người đọc giữa các phần thì giữ nhãn.

Input (công việc, VI-HUM-S07): "Việc triển khai sự thay đổi này cần được thực hiện một cách cẩn thận."

Output: "Cần triển khai thay đổi này cẩn thận."

Ba lớp danh hóa trong một câu ngắn đẩy động từ chính thành danh từ. Giữ nguyên mức nghĩa vụ "cần" và không thêm chủ thể mà input không nêu.

Input (chăm sóc khách hàng, VI-HUM-P01): "Chúng tôi gửi kèm báo giá. Bạn vui lòng phản hồi trước thứ Sáu. Quý vị có thể liên hệ tổng đài nếu cần hỗ trợ."

Output: "Chúng tôi gửi kèm báo giá. Quý khách vui lòng phản hồi trước thứ Sáu và liên hệ tổng đài nếu cần hỗ trợ."

Ba hệ xưng hô trong ba câu liền nhau; chọn một hệ đúng register rồi áp dụng nhất quán. Giữ nguyên hạn chót thứ Sáu và kênh liên hệ. Nếu không rõ nên chọn hệ nào, hỏi tác giả thay vì tự chuẩn hóa.

## Không nên sửa

Input: "Nghiên cứu có thể chưa phản ánh nhóm người trên 65 tuổi vì mẫu chỉ có 18 người ở độ tuổi này."

Output: giữ nguyên. Câu cụ thể, hedge có lý do và số liệu cần thiết.

Input: "Quý khách vui lòng mang theo căn cước công dân khi nhận thẻ."

Output: giữ nguyên nếu đây là thông báo chính thức của ngân hàng. Không đổi thành "Bạn nhớ mang CCCD nhé".

Input (hành chính): "Đơn vị chủ trì có trách nhiệm khai thác dữ liệu trong lĩnh vực quản lý đất đai theo phân cấp."

Output: giữ nguyên. "Khai thác" và "lĩnh vực" kích hoạt `VI-HUM-L06`, nhưng đây là register hành chính — chính trường `exceptions` của pattern loại trừ register này, và L06 vốn có độ tin cậy thấp cùng rủi ro dương tính giả cao. Không hạ register.

Bộ 30 ví dụ humanizer-vi có metadata theo domain và register nằm trong `examples/examples.jsonl`.
