import asyncio
import ssl
import re


def to_vis_string(dat):
  s = ''
  for i in dat:
    c = chr(i)
    if '0' <= c <= '9' or 'A' <= c <= 'Z' or 'a' <= c <= 'z' or c in ' .,!?():;<>{}[]\'\"/@~-#*-=+':
      s += c
    elif c == '\\':
      s += '\\\\'
    else:
      s += '\\x{:02x}'.format(i)
  return s


channels = set()

PASSWORD = '[REDACTED]'
USER = 'duckshooter'
NICK = 'duckotron3000'


def send(msg, writer):
  print('<<' + msg)
  writer.write('{}\r\n'.format(msg).encode('ASCII'))


def is_duck(mask, s):
  if mask != 'jmduck!~quackles@cpe-76-184-247-232.tx.res.rr.com':
    return False
  if '(' in s or ')' in s:
    return False
  t = s
  t = t.replace(' ', '')
  t = t.replace('\\xe2\\x80\\x8b', '')
  t = t.replace('\\xbb', '')
  res = t.startswith('\\xe3\\x83\\xe3\\x82\\x9c\\xe3\\x82\\x9c\\xe3\\x83\\xe3\\x80'
                     '\\x82\\xe3\\x80\\x82\\xe3\\x83\\xe3\\x82\\x9c\\xe3\\x82\\x9c')
  return res


duck_alive = False


@asyncio.coroutine
def shoot(loop, writer, delay):
  yield from asyncio.sleep(delay)
  if duck_alive:
    send('PRIVMSG ##duckhunt2 :.bang', writer)


@asyncio.coroutine
def main_listerener(loop):
  reader, writer = yield from \
    asyncio.open_connection(host='abra.me', port='6667', loop=loop,
                            ssl=ssl.create_default_context(ssl.Purpose.CLIENT_AUTH))

  send('PASS {}'.format(PASSWORD), writer)
  send('NICK {}'.format(NICK), writer)
  send('USER {0} 0 *:{0}'.format(USER), writer)
  send('JOIN #abratest', writer)
  send('JOIN ##duckhunt2', writer)

  send('PRIVMSG ##duckhunt2 :.duckstatus', writer)

  global duck_alive

  while True:
    data = yield from reader.read(1000000)
    data_s = to_vis_string(data)
    for s in data_s.split(r'\x0d\x0a'):
      if len(s) == 0:
        continue
      print('>>' + s)

      if s.count(':') < 2:
        if s.startswith('PING'):
          send('PONG :' + s.split(':')[1], writer)
        continue

      _, prefix, meat = s.split(':', maxsplit=2)
      prefix_parts = prefix.split()
      mask, command = prefix_parts[:2]

      if is_duck(mask, meat):
        duck_alive = True
        asyncio.async(shoot(loop, writer, 1.0))

      if meat.startswith('({})'.format(NICK)):
        f = re.findall(r'You can try again in (.+?) seconds.', meat)
        if f and f[0]:
          asyncio.async(shoot(loop, writer, float(f[0])))

      if command == 'KICK' and prefix_parts[3] == NICK:
        send('JOIN {}'.format(prefix_parts[2]), writer)

      if mask == 'jmduck!~quackles@cpe-76-184-247-232.tx.res.rr.com':
        print('[{}]'.format(meat))
        if re.match(r'[^ ]* you (shot|befriended) a duck.*', meat):
          print('duck dead :(')
          duck_alive = False
        elif '({}) There is a duck close enough nearby to shoot or befriend.'.format(NICK) == meat:
          duck_alive = True
          asyncio.async(shoot(loop, writer, 0.1))

  print('Close the socket')
  writer.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main_listerener(loop))
loop.close()
