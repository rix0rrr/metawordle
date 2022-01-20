import collections
import tqdm
import pickle
import sys
import pprint
import random

def correlate(answer, guess):
  """Return the matching pattern for 'guess' at 'answer'.

  Returns a string of N characters:

    . = letter of guess does not occur in answer
    O = letter of guess occurs in answer but not in the right place
    X = letter is in the right place.

  Because O only counts for letters that haven't been
  indicated with another X or O yet, we have to cross off
  letters from the answer to make sure we don't count double.
  """
  assert len(answer) == len(guess)

  # Make answer mutable, so we can cross off lettres
  answer = list(answer)

  N = len(guess)

  ret = ['.'] * N

  # First do Xes
  for i in range(N):
    if guess[i] == answer[i]:
      ret[i] = 'X'
      answer[i] = '?' # Cross off

  # Then do Os
  for i in range(N):
    if ret[i] == '.': # Not guessed yet
      try:
        j = answer.index(guess[i])
        ret[i] = 'O'
        answer[j] = '?' # Cross off
      except ValueError:
        pass
  return ''.join(ret)


def load_word_list(fname):
  with open(fname) as f:
    return [x.strip() for x in f.read().split('\n') if x.strip()]


def load_lookup():
  with open('lookup.pkl', 'rb') as f:
    return pickle.load(f)


def load_answers():
  return load_word_list('answers.txt')


def build():
  answers = load_answers()
  guesses = load_word_list('guesses.txt')

  patterns = collections.defaultdict(set)

  for answer in tqdm.tqdm(answers):
    for guess in guesses:
      if answer == guess: continue

      pattern = correlate(answer, guess)
      patterns[pattern].add(answer)

  with open('lookup.pkl', 'wb') as f:
    pickle.dump(patterns, f)


def analyze():
  lookup = load_lookup()

  print('Length', len(lookup))

  # sample = random.sample(lookup.items(), 5)
  # pprint.pprint(sample)

  counter = collections.Counter()
  for pattern, names in lookup.items():
    counter[pattern] = len(names)
  pprint.pprint(counter.most_common(237))


def reduce_by_pattern(lookup, remaining_words, pattern):
  # & is set intersection, no-op if pattern not found
  return remaining_words & lookup.get(pattern, remaining_words)


def intersect_all(lookup, patterns):
  possible_words = lookup[patterns[0]]
  print(patterns[0], '%4d' % len(possible_words), 'remaining')
  for pat in patterns[1:]:
    possible_words = possible_words & lookup[pat]
    print(pat, '%4d' % len(possible_words), 'remaining')
  return possible_words


def analyze_discriminant(lookup, word1, word2):
  """Find patterns that include word1 but not word2."""
  ret = []

  for pattern, words in lookup.items():
    # XOR presence of these words
    if (word1 in words) != (word2 in words):
      ret.append(pattern)

  return ret


def doemaarwat():
  lookup = load_lookup()

  answers = intersect_all([
    '.OOO.',
    'XXXX.',
    'OXO.O',
    'OXO..',
    '.OOXO',
    'X.OXO',
    '.XXXX',
    'OXO..',
    'XX.XX',
    'X..XX',
    'O.O.X',
    '.O.OX',
    'XOX..',
    'O.OO.',
    'X.OO.',
    '.XXXO',
    '.XOXO',
    'OOOO.',
    'X.OO.',
    'XXOXO',
    'X.OOO',
    'X...X',
    'X..XX',
    'XX.X.',
    '.OXOO',
  ])
  print(random.sample(answers, min(len(answers), 10)))

  if len(answers) == 2:
    print('We could distinguish between these with the following patterns:')
    lookup = load_lookup()
    answers = list(answers)
    print(analyze_discriminant(lookup, answers[0], answers[1]))


def impossible():
  lookup = load_lookup()
  answers = load_word_list('answers.txt')

  cnt = 0
  for a1 in tqdm.tqdm(answers):
    for a2 in answers:
      if a1 == a2: continue

      if not analyze_discriminant(lookup, a1, a2):
        cnt += 1
        tqdm.write(f'No way to distinguish between {a1}, {a2}')

  print(f'{cnt} indistinguishable words found')


if __name__ == '__main__':
  if sys.argv[1] == 'build':
    build()
  elif sys.argv[1] == 'analyze':
    analyze()
  elif sys.argv[1] == 'doewat':
    doemaarwat()
  elif sys.argv[1] == 'impossible':
    impossible()
  else:
    print('Wazeggie?')
