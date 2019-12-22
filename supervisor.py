import zmq
import json
import logging
import sys
import uuid
import socket

try:
    from zyre_pyzmq import Zyre as Pyre
except Exception as e:
    from pyre import Pyre

from pyre import zhelper
from aiohttp import web

async def handle(request):
    name = request.match_info.get('name', "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)

app = web.Application()
app.add_routes([web.get('/', handle),
                web.get('/{name}', handle)])


def chat_task(ctx, pipe):
    n = Pyre("Cluster")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    n.set_header("ip",s.getsockname()[0])
    s.close()
    n.join("Cluster")
    n.start()

    poller = zmq.Poller()
    poller.register(pipe, zmq.POLLIN)
    poller.register(n.socket(), zmq.POLLIN)
    print(n.name())
    print(n.uuid())
    while(True):
        items = dict(poller.poll())
        if pipe in items and items[pipe] == zmq.POLLIN:
            message = pipe.recv()
            # message to quit
            if message.decode('utf-8') == "$$STOP":
                break
            print("Cluster_TASK: %s" % message)
            n.shouts("Cluster", message.decode('utf-8'))
        else:
        #if n.socket() in items and items[n.socket()] == zmq.POLLIN:
            cmds = n.recv()
            msg_type = cmds.pop(0)
            print("NODE_MSG TYPE: %s" % msg_type)
            print("NODE_MSG PEER: %s" % uuid.UUID(bytes=cmds.pop(0)))
            print("NODE_MSG NAME: %s" % cmds.pop(0))
            if msg_type.decode('utf-8') == "SHOUT":
                print("NODE_MSG GROUP: %s" % cmds.pop(0))
            elif msg_type.decode('utf-8') == "ENTER":
                headers = json.loads(cmds.pop(0).decode('utf-8'))
                print("NODE_MSG HEADERS: %s" % headers)
                for key in headers:
                    print("key = {0}, value = {1}".format(key, headers[key]))
            print("NODE_MSG CONT: %s" % cmds)
    n.stop()


if __name__ == '__main__':
    logger = logging.getLogger("pyre")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False

    ctx = zmq.Context()
    chat_pipe = zhelper.zthread_fork(ctx, chat_task)

    web.run_app(app)

    chat_pipe.send("$$STOP".encode('utf_8'))
    print("FINISHED")
