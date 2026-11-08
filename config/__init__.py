# PyMySQL stands in for mysqlclient so no C toolchain / libmysqlclient is required.
import pymysql

pymysql.version_info = (2, 2, 1, "final", 0)  # satisfy Django's mysqlclient version gate
pymysql.install_as_MySQLdb()

from .celery import app as celery_app  # noqa: E402

__all__ = ("celery_app",)
