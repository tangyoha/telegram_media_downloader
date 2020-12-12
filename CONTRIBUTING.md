## Contributing

First off, thank you for considering contributing to Telegram Media Downloader. It's people like you that make telegram-media-downloader such a great tool.
Please take a moment to review this document in order to make the contribution process easy and effective for everyone involved.

### Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/Dineshkarthik/telegram_media_downloader/issues)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

If you have a general question about telegram-media-downloader, you can ask it on [Discussion](https://github.com/Dineshkarthik/telegram_media_downloader/discussions) under `Q&A`  category and any ideas/suggestions goes under `Ideas` category, the issue tracker is only for bugs and feature requests.

### Fork & create a branch

If this is something you think you can fix, then [fork telegram-media-downloader](https://help.github.com/articles/fork-a-repo) and create a branch with a descriptive name.

A good branch name would be (where issue #52 is the ticket you're working on):

```sh
	git checkout -b 52-fix-expired-file-reference
```

### For new Contributors

If you never created a pull request before, welcome [Here is a great tutorial](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github) on how to send one :)

1. [Fork](http://help.github.com/fork-a-repo/) the project, clone your fork, and configure the remotes:
```sh
   # Clone your fork of the repo into the current directory
   git clone https://github.com/<your-username>/<repo-name>
   # Navigate to the newly cloned directory
   cd <repo-name>
   # Install dependencies
   make dev_install
   # Assign the original repo to a remote called "upstream"
   git remote add upstream https://github.com/Dineshkkarthik/<repo-name>
```

2. If you cloned a while ago, get the latest changes from upstream:
```sh
   git checkout master
   git pull upstream master
```

3. Create a new branch (off the main project master branch) to contain your feature, change, or fix based on the branch name convention described above:
```sh
   git checkout -b <branch-name>
```

4. Make sure to update, or add to the tests when appropriate. Patches and features will not be accepted without tests. Run `make test` to check that all tests pass after you've made changes.

5. If you added or changed a feature, make sure to document it accordingly in the `README.md` file.

6. Push your  branch up to your fork:
```sh
   git push origin <branch-name>
```

7. [Open a Pull Request](https://help.github.com/articles/using-pull-requests/) with a clear title and description.


### Coding Standards
#### Python style
Please follow these coding standards when writing code for inclusion in telegram-media-downloader.

Telegram-media-downloader  follows the [PEP8](https://www.python.org/dev/peps/pep-0008/) standard and uses [Black](https://black.readthedocs.io/en/stable/) and [Pylint](https://pylint.pycqa.org/en/latest/) to ensure a consistent code format throughout the project.

[Continuous Integration](https://github.com/Dineshkarthik/telegram_media_downloader/actions)  using GitHub Actions will run those tools and report any stylistic errors in your code. Therefore, it is helpful before submitting code to run the check yourself:
```sh
black media_downloader.py utils
```
to auto-format your code. Additionally, many editors have plugins that will apply  `black`  as you edit files.

Writing good code is not just about what you write. It is also about  _how_  you write it. During  [Continuous Integration](https://github.com/Dineshkarthik/telegram_media_downloader/actions)  testing, several tools will be run to check your code for stylistic errors. Generating any warnings will cause the test to fail. Thus, good style is a requirement for submitting code to telegram-media-downloader.

This is already added in the repo to help contributors verify their changes before contributing them to the project:
```sh
make style_check
```

#### Type hints
Telegram-media-downloader strongly encourages the use of  [**PEP 484**](https://www.python.org/dev/peps/pep-0484)  style type hints. New development should contain type hints and pull requests to annotate existing code are accepted as well!

Types imports should follow the  `from  typing  import  ...`  convention. So rather than
```py
import typing

primes: typing.List[int] = []
```
You should write
```py
from typing import List, Optional, Union

primes: List[int] = []
```

`Optional`  should be used where applicable, so instead of
```py
maybe_primes: List[Union[int, None]] = []
```
You should write
```py
maybe_primes: List[Optional[int]] = []
```

#### Validating type hints
telegram-media-downloader uses  [mypy](http://mypy-lang.org/)  to statically analyze the code base and type hints. After making any change you can ensure your type hints are correct by running
```sh
make static_type_check
```

#### Docstrings and standards
A Python docstring is a string used to document a Python module, class, function or method, so programmers can understand what it does without having to read the details of the implementation.

The next example gives an idea of what a docstring looks like:
```py
def add(num1: int, num2: int) -> int:
    """
    Add up two integer numbers.

    This function simply wraps the ``+`` operator, and does not
    do anything interesting, except for illustrating what
    the docstring of a very simple function looks like.

    Parameters
    ----------
    num1 : int
	    First number to add.
    num2 : int
	    Second number to add.

    Returns
    -------
    int
	    The sum of ``num1`` and ``num2``.

    See Also
    --------
    subtract : Subtract one integer from another.

    Examples
    --------
    >>> add(2, 2)
    4
    >>> add(25, 0)
    25
    >>> add(10, -10)
    0
    """
    return num1 + num2
```
Some standards regarding docstrings exist, which make them easier to read, and allow them be easily exported to other formats such as html or pdf.

### Code of Conduct

As a contributor, you can help us keep the  community open and inclusive. Please read and follow our  [Code of Conduct](https://github.com/Dineshkarthik/telegram_media_downloader/blob/master/CODE_OF_CONDUCT.md).