-- 1. Count per group: how many books are in each genre?
SELECT genre, COUNT(*) AS book_count
FROM books
GROUP BY genre
ORDER BY genre;


-- 2. Ratio per group above a threshold:
--    which genres have more than 30% of their books unavailable?
SELECT genre,
       COUNT(*) AS total,
       COUNT(*) FILTER (WHERE NOT available) AS unavailable,
       ROUND(CAST(COUNT(*) FILTER (WHERE NOT available) AS NUMERIC) / COUNT(*), 2) AS unavailable_ratio
FROM books
GROUP BY genre
ORDER BY genre;


-- 3. Comparing two locations:
--    which members borrowed a book from a library other than their home library?
SELECT members.name, members.home_library_id, loans.library_id AS borrowed_at_library_id
FROM members
JOIN loans ON loans.member_id = members.id
ORDER BY members.name;


-- 4. A table joined to itself: which members did Ada Park refer?
SELECT members.name
FROM members
JOIN members AS referrer ON referrer.id = members.referred_by_id
WHERE referrer.name = 'Ada Park'
ORDER BY members.name;
