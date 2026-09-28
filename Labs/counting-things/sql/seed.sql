INSERT INTO libraries (id, name, city) VALUES
    (1, 'Central',   'Springfield'),
    (2, 'Riverside', 'Springfield'),
    (3, 'Hilltop',   'Shelbyville');

INSERT INTO books (id, title, author, genre, pages, available) VALUES
    (1,  'Pride and Prejudice',           'Jane Austen',         'Fiction',         432, TRUE),
    (2,  'Middlemarch',                   'George Eliot',        'Fiction',         880, FALSE),
    (3,  'Beloved',                       'Toni Morrison',       'Fiction',         324, TRUE),
    (4,  'The Great Gatsby',              'F. Scott Fitzgerald', 'Fiction',         180, TRUE),
    (5,  'Things Fall Apart',             'Chinua Achebe',       'Fiction',         209, TRUE),
    (6,  'Moby-Dick',                     'Herman Melville',     'Fiction',         635, TRUE),
    (7,  'The Hound of the Baskervilles', 'Arthur Conan Doyle',  'Mystery',         256, FALSE),
    (8,  'Murder on the Orient Express',  'Agatha Christie',     'Mystery',         256, TRUE),
    (9,  'The Big Sleep',                 'Raymond Chandler',    'Mystery',         231, FALSE),
    (10, 'The Maltese Falcon',            'Dashiell Hammett',    'Mystery',         217, TRUE),
    (11, 'Gaudy Night',                   'Dorothy L. Sayers',   'Mystery',         501, TRUE),
    (12, 'Dune',                          'Frank Herbert',       'Science Fiction', 412, TRUE),
    (13, 'The Left Hand of Darkness',     'Ursula K. Le Guin',   'Science Fiction', 304, FALSE),
    (14, 'Foundation',                    'Isaac Asimov',        'Science Fiction', 255, TRUE),
    (15, 'Kindred',                       'Octavia E. Butler',   'Science Fiction', 264, TRUE),
    (16, 'The Guns of August',            'Barbara W. Tuchman',  'History',         511, TRUE),
    (17, 'SPQR',                          'Mary Beard',          'History',         608, FALSE),
    (18, 'The Silk Roads',                'Peter Frankopan',     'History',         636, TRUE),
    (19, 'Leaves of Grass',               'Walt Whitman',        'Poetry',          145, TRUE),
    (20, 'Ariel',                         'Sylvia Plath',        'Poetry',           96, TRUE);

INSERT INTO members (id, name, home_library_id, referred_by_id) VALUES
    (1, 'Ada Park',       1, NULL),
    (2, 'Ben Okafor',     1, 1),
    (3, 'Cleo Martin',    2, 1),
    (4, 'Dev Sharma',     2, NULL),
    (5, 'Esme Lindqvist', 3, 1),
    (6, 'Farid Haddad',   3, 4),
    (7, 'Grace Kim',      1, 4),
    (8, 'Hugo Brandt',    2, 3);

INSERT INTO loans (id, member_id, book_id, library_id) VALUES
    (1,  1, 1,  1),
    (2,  1, 7,  1),
    (3,  2, 2,  1),
    (4,  2, 16, 1),
    (5,  3, 8,  2),
    (6,  3, 12, 1),
    (7,  4, 13, 2),
    (8,  5, 17, 3),
    (9,  5, 9,  1),
    (10, 6, 3,  3),
    (11, 7, 18, 3),
    (12, 8, 10, 2);
