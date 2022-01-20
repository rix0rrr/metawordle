"""filedict.py
a Persistent Dictionary in Python

Author: Erez Shinan
Date  : 24-May-2009
"""

import sqlite3
import pickle

class DefaultArg:
    pass

class Solutions:
    Sqlite3 = 0

class FileDict(object):
    "A dictionary that stores its data persistantly in a file"

    def __init__(self, solution=Solutions.Sqlite3, **options):
        assert solution == Solutions.Sqlite3
        try:
            self.__conn = options.pop('connection')
        except KeyError:
            filename = options.pop('filename')
            self.__conn = sqlite3.connect(filename)

        self.__tablename = options.pop('table', 'dict')

        self._nocommit = False

        assert not options, "Unrecognized options: %s" % options

        self.__conn.execute('create table if not exists %s (key blob, value blob);'%self.__tablename)
        self.__conn.execute('create index if not exists %s_index ON %s(key);' % (self.__tablename, self.__tablename))
        self.__conn.commit()

    def _commit(self):
        if self._nocommit:
            return

        self.__conn.commit()

    def __pack_key(self, key):
        return sqlite3.Binary(pickle.dumps(key, 1))
    def __pack_value(self, value):
        return sqlite3.Binary(pickle.dumps(value, -1))
    def __unpack_value(self, value):
        return pickle.loads(value)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

    def __getitem__(self, key):
        tbl = self.__tablename
        key_pickle = self.__pack_key(key)
        c = self.__conn.execute('select value from %s where key=?;'%tbl, (key_pickle,))
        res = c.fetchone()
        if res is None:
            raise KeyError(key)

        [value_pickle] = res
        return self.__unpack_value(value_pickle)

    def __setitem(self, key, value):
        tbl = self.__tablename
        key_pickle = self.__pack_key(key)
        value_pickle = self.__pack_value(value)

        res = self.__conn.execute('update %s set value=? where key=?;'%tbl, (value_pickle, key_pickle) )
        if res.rowcount <= 0:
            res = self.__conn.execute('insert into %s values (?, ?);'%tbl, (key_pickle, value_pickle) )

        assert res.rowcount == 1

    def __setitem__(self, key, value):
        self.__setitem(key, value)
        self._commit()

    def __delitem__(self, key):
        tbl = self.__tablename
        key_pickle = self.__pack_key(key)

        res = self.__conn.execute('delete from %s where key=?;'%tbl, (key_pickle,))
        if res.rowcount <= 0:
            raise KeyError(key)

        self._commit()

    def update(self, d):
        for k,v in d.iteritems():
            self.__setitem(k, v)
        self._commit()

    def pop(self, key, default=DefaultArg):
        try:
            value = self[key]
        except KeyError:
            if default is DefaultArg:
                raise
            else:
                value = self.get(key, default)
        else:
            del self[key]
        return value

    def keys(self):
        return (self.__unpack_value(x[0]) for x in self.__conn.execute('select key from %s;'%self.__tablename) )
    def values(self):
        return (self.__unpack_value(x[0]) for x in self.__conn.execute('select value from %s;'%self.__tablename) )
    def items(self):
        return (map(self.__unpack_value, x) for x in self.__conn.execute('select key,value from %s;'%self.__tablename) )
    def iterkeys(self):
        return self.keys()
    def itervalues(self):
        return self.values()
    def iteritems(self):
        return self.items()

    def has_key(self, key):
        tbl = self.__tablename
        key_pickle = self.__pack_key(key)
        c = self.__conn.execute('select count(*) from %s where key=?;' % tbl, (key_pickle,))
        res = c.fetchone()
        assert res
        assert 0 <= res[0] <= 1

        return bool(res[0])

    def __contains__(self, key):
        return self.has_key(key)

    def __len__(self):
        return self.__conn.execute('select count(*) from %s;' % self.__tablename).fetchone()[0]

    def __del__(self):
        try:
            self.__conn
        except AttributeError:
            pass
        else:
            self.__conn.commit()
            self.__conn.close()

    @property
    def batch(self):
        return self._Batch(self)

    class _Batch:
        def __init__(self, d):
            self.__d = d

        def __enter__(self):
            self.__d._nocommit = True
            return self.__d

        def __exit__(self, type, value, traceback):
            self.__d._nocommit = False
            self.__d._commit()
            return True
