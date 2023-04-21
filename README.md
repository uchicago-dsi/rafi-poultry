# clinic-sample

The goal of this repository is to be a central location for documenting and version controlling best practices for developing 11th Hour Data Science projects. When updating this repository the following principals should be followed:
- Low overhead on developers: These repositories are often used by clinc students so tools used here should not require additional learning to use unless absolutely necessary.
- Up to date with best practices: The tools used here should adhere as closely as possible to modern and popular methods
- Justify decisions: Decisions should be justified so future collaborators can make informed decisions as conditions change

## Usage

The file ``DataPolicy.md" contains the _default_ data and code sharing policies for the project.

To use these template in a repository:;



## Linter

To check for style, we use `flake8`, `black`, and `isort`. These are all run using `pre-commit`. [pre-commit](https://pre-commit.com/) is a tool for managing git hook scripts that we can use to run code checkers before git actions (like run `flake8` before every commit). If it fails, the commit will be blocked and the user will be shown what needs to be changed. We configure our linters with [setup.cfg](https://docs.python.org/3/distutils/configfile.html)


## GitHub

To run checkers on pull requests to `main` and `dev`, we use the `.github/workflows/main.workflow.yml` file.
