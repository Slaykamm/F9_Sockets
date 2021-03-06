import os

from aiohttp import web

WS_FILE  = os.path.join(os.path.dirname(__file__), 'websocket.html')

async def wshandler(request: web.Request):
    resp = web.WebSocketResponse()      # Для начала создаём объект HTTP-ответа:
    available = resp.can_prepare(request) #проверяем, можем ли ответить сразу в запрос, а такое возможно, только если используется веб-сокет.
    print('request', request)          #
    print('available', available)          #
    if not available:                   #Если же используется традиционный HTTP-запрос, то нужно отдать HTML-страницу, 
        with open(WS_FILE, "rb") as fp:                 #которая, в свою очередь, будет содержать код, использующий веб-сокет
            return web.Response(body=fp.read(), content_type="text/html")

    await resp.prepare(request)     #открываем соединение через веб-сокеты, ведь мы это можем.
    await resp.send_str("Welcome!!!")  #И шлём приветственное сообщение

    try:                        #Теперь настало время отослать всем пользователям, что у нас новый пользователь
        print("Someone joined.")
        for ws in request.app["sockets"]:    # cписок для хранения всех соединений
            await ws.send_str("Someone joined")
        request.app["sockets"].append(resp)

        async for msg in resp:              #Далее мы начинаем перебирать сообщения, которые пришли от пользователя
            if msg.type == web.WSMsgType.TEXT:  #Обратите внимание, что resp не содержит все сообщения, которые пользователь переслал, 
                for ws in request.app["sockets"]:  #а передает их по одному через асинхронный вариант for цикла.
                    if ws is not resp:              #То есть resp представляет собой итератор, который отдаёт сообщения по одному, когда они приходят.
                        await ws.send_str(msg.data)  # А когда их нет, то выполнение программы передаётся в Event Loop, который и следит за приходящими сообщениями.
            else:
                return resp
        return resp

    finally:                                # убираем соединение из списка
        request.app["sockets"].remove(resp)     ## Рассылаем сообщение о разрыве соединения
        print("Someone disconnected.")
        for ws in request.app["sockets"]:
            await ws.send_str("Someone disconnected.")  #Мы удаляем соединение из списка, а всем пользователям сообщаем, что пользователь отключился


async def on_shutdown(app: web.Application):  #По сути, мы здесь просто передаём всем клиентам, что соединение закрылось. 
    for ws in app["sockets"]:                   #Список app["sockets"] очищать не нужно, ведь больше мы его использовать не будем, а память и без нас очистится.
        await ws.close() 


def init():
    app = web.Application()
    app["sockets"] = []
    app.router.add_get("/", wshandler) # wshandler е   добавляет обработчик для GET-запросов по пути "/". 
                                            #В нём же мы будем проверять: был это обычный GET-запросов, по которому #
                                            # мы отдадим код страницы, или же запрос на websocket соединение.
    app.on_shutdown.append(on_shutdown) # on_shutdown
    return app


web.run_app(init())