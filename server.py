import socket
import urllib.parse
import _thread

from utils import log

from routes import error

from routes_todo import route_dict as todo_routes
from routes_user import route_dict as user_routes


# 定义一个 class 用于保存请求的数据
class Request(object):
    def __init__(self, raw_data):
        # 只能 split 一次，因为 body 中可能有换行
        header, self.body = raw_data.split('\r\n\r\n', 1)
        h = header.split('\r\n')

        parts = h[0].split()
        self.method = parts[0]
        path = parts[1]
        self.path = ""
        self.query = {}
        self.parse_path(path)
        log('Request: path 和 query', self.path, self.query)

        self.headers = {}
        self.cookies = {}
        self.add_headers(h[1:])
        self.add_cookies()
        log('Request: headers 和 cookies', self.headers, self.cookies)

    def add_cookies(self):
        """r
        Cookie:user=yang;login_time=xx;
        =>
        {
        'user':'yang',
        'login_time':'xx',
        }
        """
        cookies = self.headers.get('Cookie', '')
        kvs = cookies.split('; ')
        log('cookie', kvs)
        for kv in kvs:
            if '=' in kv:
                k, v = kv.split('=')
                self.cookies[k] = v

    def add_headers(self, header):
        """
        Accept-Lanyangge: zh-CN,zh;q=0.8
        """
        lines = header
        for line in lines:
            k, v = line.split(': ', 1)
            self.headers[k] = v

    def form(self):
        body = urllib.parse.unquote(self.body)
        args = body.split('&')
        f = {}
        for arg in args:
            k, v = arg.split('=')
            f[k] = v
        return f

    def parse_path(self, path):
        """
        输入: /yang?message=hello&author=yang
        返回
        (yang, {
            'message': 'hello',
            'author': 'yang',
        })
        """
        index = path.find('?')
        if index == -1:
            self.path = path
            self.query = {}
        else:
            path, query_string = path.split('?', 1)
            args = query_string.split('&')
            query = {}
            for arg in args:
                k, v = arg.split('=')
                query[k] = v
            self.path = path
            self.query = query


def response_for_path(request):
    """
    根据 path 调用相应的处理函数
    没有处理的 path 会返回 404
    """
    r = {}
    # 注册外部的路由
    r.update(todo_routes())
    r.update(user_routes())
    response = r.get(request.path, error)
    return response(request)


def process_request(connection):
    r = connection.recv(1024)
    r = r.decode()
    log('request log:\n{}'.format(r))
    # 把原始请求数据传给 Request 对象
    request = Request(r)
    # 用 response_for_path 函数来得到 path 对应的响应内容
    response = response_for_path(request)
    log("response log:\n{}".format(response.decode()))
    # 把响应发送给客户端
    connection.sendall(response)
    # 处理完请求, 关闭连接
    connection.close()


def run(host, port):
    """
    启动服务器
    """
    # 初始化 socket 套路
    # 使用 with 可以保证程序中断的时候正确关闭 socket 释放占用的端口
    log('开始运行于', '{}:{}'.format(host, port))
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        # 无限循环来处理请求
        while True:
            connection, address = s.accept()
            # 第二个参数类型必须是 tuple
            log('ip {}'.format(address))
            _thread.start_new_thread(process_request, (connection,))


if __name__ == '__main__':
    # 生成配置并且运行程序
    config = dict(
        host='127.0.0.1',
        port=3333,
    )
    run(**config)
