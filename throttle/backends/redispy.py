# -*- coding: utf-8 -*-
import hashlib

from throttle.backends.base import ThrottleBackendBase
try:
    import redis
    from redis.exceptions import NoScriptError
except ImportError:
    from throttle.exceptions import ThrottleImproperlyConfigured
    raise ThrottleImproperlyConfigured("django-throttle-requests is configured to use redis, but redis-py is not installed!")

# Lua script to update bucket data atomically.
# In general, lua scripts should be used instead of Redis transactions to ensure atomicity. Transactions may ne
# deprecated at some point. Also, nutcracker/twemproxy does not support transactions but does support scripting
# as long as all keys used by the script hash to the same backend.
#
# Script takes 1 key and 4 arguments: <bucket_num>, <bucket_num_next>, <bucket_span>, <cost>
INCR_BUCKET_SCRIPT = """
local newval = redis.call('hincrby', KEYS[1], ARGV[1], ARGV[4])
redis.call('hdel', KEYS[1], ARGV[2])
redis.call('expire', KEYS[1], ARGV[3])
return newval
"""

INCR_BUCKET_SCRIPT_SHA1 = hashlib.sha1(INCR_BUCKET_SCRIPT.encode('utf-8')).hexdigest()

class RedisBackend(ThrottleBackendBase):
    def __init__(self):
        self.pool = redis.ConnectionPool(host='localhost', port=6379, db=0)

    def incr_bucket(self, zone_name, bucket_key, bucket_num, bucket_num_next, bucket_span, cost=1):
        conn = redis.Redis(connection_pool=self.pool)

        bucket_cache_key = "%s:%s" % (zone_name, bucket_key)

        # Don't want to use redispy's `register_script` command here, because it uses SCRIPT LOAD, which isn't compatible
        # with nutcracker or Redis Cluster.
        try:
            try:
                return conn.evalsha(INCR_BUCKET_SCRIPT_SHA1, 1, bucket_cache_key, bucket_num, bucket_num_next, bucket_span, cost)
            except NoScriptError:
                return conn.eval(INCR_BUCKET_SCRIPT, 1, bucket_cache_key, bucket_num, bucket_num_next, bucket_span, cost)

        except redis.ConnectionError:
            return cost
