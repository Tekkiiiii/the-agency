# Đánh giá bản biên tập

Chấm theo rubric chung trong `benchmarks/rubric.md`: naturalness, clarity, meaning preservation, factual preservation, register fit, terminology consistency, edit necessity và over-editing avoidance.

Trình tự review:

1. Kiểm blocker trước. Có blocker thì fail dù kết quả đọc trôi chảy.
2. Đối chiếu từng ý với input và context được cung cấp.
3. Đọc riêng output để đánh giá độ tự nhiên.
4. Kiểm những chỗ không cần sửa có được giữ lại không.

Không dùng AI detector làm thước đo chất lượng.

## Độ tin cậy detector và dương tính giả

Detector chuyên cho tiếng Việt đạt số liệu cao trong phòng thí nghiệm. VietBinoculars dùng cặp PhoGPT-4B làm observer và PhoGPT-4B-Chat làm performer để tính tỉ số perplexity trên cross-perplexity, đạt F1 và accuracy 99–100% trên dữ liệu báo chí và văn học out-of-domain [c4147849]. VietAIDetector đóng gói cùng thuật toán đó kèm cửa sổ trượt để xử lý tài liệu dài [98907b8b].

Detector đa ngôn ngữ thì không. Trong thử nghiệm "Capybara" — người dùng cố tình nhét từ khóa dị thường vào prompt để đẩy perplexity lên — GPTZero và DetectGPT chỉ đạt 14.29%, Ghostbuster 33.33%, VietBinoculars ở ngưỡng Closest Point đạt 80.95%; Turnitin không hỗ trợ tiếng Việt trong thử nghiệm này [c4147849].

Ngay cả bản tốt nhất cũng phải hạ ngưỡng để tránh phạt oan. Ngưỡng an toàn học thuật của VietBinoculars đặt ở 0.70, đánh đổi độ nhạy để giữ tỉ lệ báo động giả quanh 6 trên 10.000 bài của người thật [c4147849].

Dương tính giả là hệ quả của cách đo, không phải lỗi cấu hình. Detector chấm perplexity: từ ngữ càng dễ đoán, điểm càng nghiêng về AI. Văn bản hành chính, pháp lý, học thuật và báo chí chính thống bắt buộc dùng thuật ngữ cố định, cụm chuyển ý chuẩn và cú pháp quy phạm, nên phân phối ngôn ngữ của chúng trùng với phân phối của AI [00e478a7, a5bb48c4]. Điểm cao ở nhóm văn bản này là điều phải xảy ra và không nói gì về tác giả. Cùng cơ chế đó tạo ra định kiến với người viết không phải bản ngữ: nghiên cứu Stanford (Weixin Liang, 2023, tạp chí Patterns) ghi nhận 61% bài luận TOEFL do người viết bị gắn cờ nhầm là AI [a5bb48c4, 77a0c856]. Turnitin ẩn điểm dưới 20%, tự khuyến cáo không dùng điểm đó làm bằng chứng duy nhất, và nhiều đại học đã tắt hẳn tính năng này [a5bb48c4].

Mức tin cậy không đều. Số liệu VietBinoculars và VietAIDetector đến từ arXiv 2509.26189 và 2608.25478 — cao. Phần Turnitin và nghiên cứu Stanford ở đây chỉ truy được đến trang giới thiệu công cụ thương mại trong bộ nguồn, chưa về tới bài gốc — thấp hơn, dùng như tham khảo.

Quy tắc vận hành: không bao giờ dẫn điểm detector làm bằng chứng trong một bản review. Không ghi điểm đó vào output, không mở hay đóng nhận xét bằng nó, không dùng nó để chọn mức can thiệp. Mọi nhận xét phải chỉ vào câu chữ cụ thể và tác động lên người đọc. Phần này củng cố anti-goal của skill là không suy đoán tác giả là AI, và không biến skill thành công cụ phát hiện.
