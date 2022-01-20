import os
import twitter
import pprint
import lookup
import random
import datetime
import filedict
import typing
from dataclasses import dataclass


YELLOW_BOX = '\U0001f7e8'
GREEN_BOX = '\U0001f7e9'
BLACK_BOX = '\u2b1b'
GREY_BOX = '\u2b1c'

INVISIBLE_CRAP = '\ufe0f'

BOXES = {
    YELLOW_BOX: 'O',
    GREEN_BOX: 'X',
    GREY_BOX: '.',
    BLACK_BOX: '.',
    }


state = filedict.FileDict(filename='state.db')


def todays_wordle_number():
  return (datetime.date.today() - datetime.date(2021, 6, 19)).days


def main():
  # username: MetaWordle
  API_KEY = os.environ['API_KEY']
  API_SECRET = os.environ['API_SECRET']
  ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
  ACCESS_TOKEN_SECRET = os.environ['ACCESS_TOKEN_SECRET']

  api = twitter.Api(
      consumer_key=API_KEY,
      consumer_secret=API_SECRET,
      access_token_key=ACCESS_TOKEN,
      access_token_secret=ACCESS_TOKEN_SECRET)

  todays_wordle = todays_wordle_number()
  print(f'Today\'s Wordle: {todays_wordle}')


  done_key = f'solution{todays_wordle}'
  if done_key in state:
    print(f'Wordle {todays_wordle} already solved: {state[done_key]}')
    return

  proc = TweetProcessor(api)
  result = proc.search_wordles(todays_wordle)
  if result:
    print(result)
    state[done_key] = result

    contributors = ['@' + x for x in result.contributors]
    the_answer = result.word.upper()
    while True:
      status = f'Based on the solutions posted by {", ".join(contributors)}, the answer to Wordle {todays_wordle} is: {the_answer}. Thanks all!'
      if len(status) <= 280:
        break

      # Otherwise, strip off a contributor
      contributors = random.sample(contributors, len(contributors) - 1)

    # api.PostUpdate(status)


@dataclass
class Solution:
  number: int
  word: str
  contributors: typing.Set[str]


class TweetProcessor:
  def __init__(self, api):
    self.api = api
    self.pattern_lookup = lookup.load_lookup()
    self.useful_patterns = []
    self.useful_users = set([])
    self.remaining_words = set(lookup.load_answers())
    self.done = False
    self.max_pages = 60

  def search_wordles(self, wordle_num):
    max_id = None

    for page in range(self.max_pages):
      if self.done: break

      print(f'Page {page + 1}')

      raw_query = f'q=wordle%20{wordle_num}%206&f=live&count=100'
      if max_id:
        raw_query += f'&max_id={max_id}'
      tweets = self.api.GetSearch(raw_query=raw_query)

      # Random sampling to give ourselves an opportunity to skip tweets
      # that mess us up.
      selection = random.sample(tweets, min(50, len(tweets)))

      self.handle_results_page(selection, wordle_num)
      max_id = tweets[-1].id

    print('Remaining words', self.remaining_words)
    print('Patterns', len(self.useful_patterns), self.useful_patterns)
    print('Users', len(self.useful_users), self.useful_users)

    if len(self.remaining_words) == 1:
      return Solution(number=wordle_num,
          word=next(iter(self.remaining_words)),
          contributors=self.useful_users)

  def handle_results_page(self, tweets, wordle_num):
    print(f'{len(tweets)} tweets found')
    for tweet in tweets:
      if self.done: break

      if f'Wordle {wordle_num}' not in tweet.text:
        continue

      # Different Wordle instance than we're looking for, either
      # worlde.wekeke.com or the German wordle, or Russian
      #
      # We are only looking for the powerlanguage.co.uk one (which has no
      # ads or links in the body)
      bad_wordle_markers = ['https://t.co', 'Wordle (RU)']
      if any(w in tweet.text for w in bad_wordle_markers):
        continue

      lines = tweet.text.split('\n')
      patterns = [(l, unicode_to_xes(l)) for l in lines if is_wordle_pattern(l)]

      for uni, pattern in patterns:
        if self.done: break

        before = 'proxy' in self.remaining_words
        self.try_pattern(tweet.user.screen_name, uni, pattern)

        if before and 'proxy' not in self.remaining_words:
          print(tweet.text)


  def try_pattern(self, screen_name, uni, pattern):
    new_remaining_words = lookup.reduce_by_pattern(self.pattern_lookup, self.remaining_words, pattern)

    if not new_remaining_words:
      # This reduced our set of possible answers to 0. Ignore!
      return

    if len(new_remaining_words) < len(self.remaining_words):
      self.remaining_words = new_remaining_words

      self.useful_patterns.append(pattern)
      self.useful_users.add(screen_name)

      print(f'{screen_name:25} | {uni} {pattern} | {len(new_remaining_words)} remaining {"proxy" in new_remaining_words}')

      if len(self.remaining_words) < 2:
        self.done = True



def is_wordle_pattern(x):
  """Return whether this line looks like 5 subsequent colored wordle blocks."""
  x = x.replace(INVISIBLE_CRAP, '')
  return len(x) == 5 and all(c in BOXES for c in x)


def unicode_to_xes(uni):
  """Convert unicode characters to our ASCII representation of patterns."""
  uni = uni.replace(INVISIBLE_CRAP, '')
  return ''.join(BOXES[c] for c in uni)


if __name__ == '__main__':
  main()
