#!/usr/bin/python3
import requests
import time
import argparse
from concurrent.futures import ThreadPoolExecutor

class User:
    def __init__(self, hub_url, username, password):
        self.hub_url = hub_url
        self.username = username
        self.password = password
        self.session = requests.Session()

    def login(self):
        r = self.session.post(
            self.hub_url + '/hub/login',
            data={'username': self.username, 'password': self.password}
        )
        r.raise_for_status()

    def start_server(self):
        # Using this and not the API since it seems there isn't an easy
        # way to find out if the server has fully started?
        next_url = self.hub_url + '/hub/spawn'
        # give each spawner 2 minutes to redirect correctly
        for i in range(120):
            expected_url = self.hub_url + '/user/' + self.username + '/tree'
            r = self.session.get(next_url)
            r.raise_for_status()
            next_url = r.url
            if next_url.startswith(expected_url):
                return True
            else:
                if not next_url.startswith(self.hub_url + '/hub/user/%s' % self.username):
                    print("unexpected %s != %s" % (next_url, expected_url))
                time.sleep(1)
        else:
            print("%s != %s" % (next_url, expected_url))
            return False
        return True

    def stop_server(self):
        url = '{}/hub/api/users/{}/server'.format(self.hub_url, self.username)
        # These hacks seem to be needed for talking to the API like this?
        host = self.hub_url.split('//', 1)[1] + '/hub'
        self.session.delete(url, headers={'referer': host}).raise_for_status()

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        'hub_url',
    )
    argparser.add_argument(
        'total_users',
        type=int
    )
    argparser.add_argument(
        'parallel_users',
        type=int
    )

    args = argparser.parse_args()

    def simulate_user(n):
        u = User(args.hub_url, n, 'wat')
        try:
            u.login()
            result = u.start_server()
        except Exception as e:
            print("User %s failed" % n, e)
            return False
        else:
            u.stop_server()
            return result

    executor = ThreadPoolExecutor(max_workers=args.parallel_users)
    futures = []
    for i in range(args.total_users):
        futures.append(executor.submit(simulate_user, 'user-{}-{}-{}'.format(args.total_users, args.parallel_users, i)))

    counts = {True: 0, False: 0}
    for i, f in enumerate(futures):
        counts[f.result()] += 1
        if (i+1) % min(args.parallel_users, 20) == 0:
            print(i+1, counts)

if __name__ == '__main__':
    main()
