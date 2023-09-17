"""
Schema for the sqlite3 database used by Stash.
"""

schema = [
    """
    create table preferences (
        name text not null,
        value text,
        target text not null,
        unique (name, target)
        on conflict replace
    )""",

    """
    create table files (
        _file_id integer primary key autoincrement,
        hash text not null unique,
        filename text,
        timestamp datetime
    )""",

    """
    create index file_index on files(_file_id)
    """,

    """
    create table keywords (
        _keyword_id integer primary key autoincrement,
        _keyword text,
        unique(_keyword_id, _keyword)
    )""",

    """
    create index keyword_index on keywords(_keyword_id)
    """,

    """
    create table keyword_x_file (
        id integer primary key autoincrement,
        _file_id integer references files,
        _keyword_id integer references keywords
    )"""
]
