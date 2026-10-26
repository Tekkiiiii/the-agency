# Workflow biên tập

## 1. Lập biên bản bảo toàn

Trước khi sửa, ghi nhanh các thành phần không được đổi: số liệu, tên, mốc thời gian, trích dẫn, phủ định, điều kiện, mức chắc chắn và thuật ngữ. Với văn bản ngắn, có thể giữ danh sách này trong suy luận. Với tài liệu dài, lập bảng.

## 2. Chẩn đoán ở ba tầng

Đọc theo thứ tự đoạn, câu, từ. Ở tầng đoạn, xem mạch lập luận và phần mở hoặc kết. Ở tầng câu, xem chủ thể, hành động, quan hệ logic và nhịp. Chỉ ở tầng từ mới xét cụm sáo, danh hóa hoặc từ nối.

## 3. Chọn mức can thiệp

- Nhẹ: sửa lỗi cục bộ, giữ cấu trúc và giọng.
- Vừa: gộp hoặc tách câu, bỏ lời dẫn thừa, làm rõ chủ thể.
- Sâu: sắp xếp lại đoạn khi cấu trúc che khuất luận điểm. Đối chiếu biên bản bảo toàn sau mỗi đoạn.

## 4. Audit hai chiều

So output với input để tìm dữ kiện bị mất. Sau đó chỉ đọc output để tìm nhịp gượng, thuật ngữ lệch và câu nối thiếu logic. Hai lượt này tìm hai loại lỗi khác nhau.

## 5. Sáu thao tác sửa thường dùng

Nhịp câu. Văn bản đều giọng thường vì mọi câu dài xấp xỉ nhau. Chen câu rất ngắn, ba đến năm chữ, giữa các câu ghép; đổi vị trí trạng ngữ; tách mệnh đề phụ dài thành câu độc lập [eefd573e, a5bb48c4].

Chi tiết bản địa cụ thể. Thay ví dụ kiểu sách giáo khoa bằng thực thể có thật: tên doanh nghiệp, số liệu có nguồn, bối cảnh vùng miền [9b106d82, eefd573e]. Chỉ thay khi dữ kiện đã có trong input hoặc context được cung cấp. Bịa thực thể mới là blocker.

Quan điểm cá nhân. Khi bản gốc đã có lập trường, viết lập trường đó thành câu rõ thay vì liệt kê mọi phía rồi bỏ lửng [9c380dc4]. Văn bản trung lập thì giữ trung lập.

Xưng hô đúng độc giả. Lỗi hay gặp nhất là "bạn" dịch máy từ "you" và việc trộn tôi, mình, chúng ta, quý vị trong cùng một bài [eefd573e, 77a0c856]. Chọn một hệ đại từ theo quan hệ thật giữa người viết và người đọc rồi giữ nhất quán đến cuối.

Khẩu ngữ đúng liều. Ở văn cảnh đời thường, blog hay chăm sóc khách hàng, vài từ tình thái cuối câu (nhé, nhỉ, à, ạ, thôi, mà) làm câu bớt vô trùng [eefd573e, 77a0c856]. Ở văn bản hành chính, pháp lý, học thuật thì không thêm.

Tái cấu trúc đoạn. Bỏ tiêu đề phụ dựng cho từng ý nhỏ. Gộp bullet thành đoạn văn khi nội dung không phải danh sách thật. Cho các đoạn có độ dài khác nhau thay vì đối xứng đều [eefd573e].

## Ba lối sửa hỏng

1. Thay từ đồng nghĩa máy móc. Tra từ điển đổi những từ nằm trong catalog mà giữ nguyên khuôn cấu trúc thì không sửa được gì; người đọc vẫn thấy cách sắp ý rập khuôn [eefd573e]. Quy trình đã đặt sửa cấu trúc trước khi thay từ ở bước 4 của SKILL.md. Theo đúng thứ tự đó.
2. Cắt câu vụn. Chặt mọi câu dài thành câu đơn ngắn làm đứt mạch lập luận, nặng nhất ở văn nghị luận, học thuật và báo chí. Bản ra rời rạc và mất liên kết.
3. Công cụ "humanize" tự động. Các công cụ này tráo từ vựng vụng về: đo trên bản thử thực tế, HIX Bypass mắc 8 lỗi ngữ pháp trong đoạn 80 từ và Bypass AI mắc 7 lỗi trên 100 từ, tức khoảng 7-8 lỗi mỗi 100 từ [369062e8]. Bản ra thường không đọc nổi. Con số này lấy từ một bài Reddit dịch lại, không phải nghiên cứu bình duyệt; coi là chỉ dấu định tính.

## Khi nên hỏi lại

Hỏi khi có nhiều độc giả khả dĩ với register khác hẳn nhau, đại từ cần lựa chọn quan hệ xã hội, hoặc câu mơ hồ khiến mỗi cách hiểu dẫn đến dữ kiện khác. Nếu chỉ khác sở thích nhỏ, chọn phương án ít can thiệp.
