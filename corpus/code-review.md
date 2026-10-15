# Code review

## Requirements
Every change to a production service needs **one approving review**; changes touching authentication, billing or
data deletion need **two**, one of them from a code owner. Authors may not approve their own pull requests.

## Size
Pull requests should stay under **400 changed lines**. Larger changes must be split, or carry a note explaining why
they can't be, and get a synchronous walkthrough with the reviewer.

## Turnaround
Reviewers should give a first response within **one business day**. If a review is blocking a release, ask in
`#code-review` rather than pinging individuals.

## What reviewers check
Correctness and tests first; then security (input validation, authorisation, secrets); then readability. Style
nits that a linter could catch are not review comments: add the linter rule instead.
