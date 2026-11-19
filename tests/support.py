"""来源契约测试工具；不包含采集实现。"""
from contextlib import ExitStack
import http.client
import json
import unittest
from urllib.parse import urlsplit
from source.server import running_source

class SourceCase(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack()
        self.base,self.source=self.stack.enter_context(running_source())
        self.addCleanup(self.stack.close)
    def request(self,path,method="GET",body=None,headers=None):
        u=urlsplit(self.base)
        connection=http.client.HTTPConnection(u.hostname,u.port,timeout=10)
        if isinstance(body,dict):
            body=json.dumps(body).encode()
            headers=dict(headers or {},**{"Content-Type":"application/json"})
        connection.request(method,path,body=body,headers=headers or {})
        r=connection.getresponse()
        status,h,data=r.status,dict(r.getheaders()),r.read()
        connection.close()
        return status,h,data
    def control(self,stage,**options):
        self.assertEqual(self.request("/__control","POST",dict(stage=stage,**options))[0],200)
