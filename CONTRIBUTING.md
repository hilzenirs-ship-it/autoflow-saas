# Contributing to AutoFlow SaaS

First off, thanks for taking the time to contribute! ❤️

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**
* **Include your environment details** (OS, Python version, Flask version, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and the expected new behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Follow the Python styleguide (PEP 8)
* Include appropriate test cases
* Update documentation as needed
* End all files with a newline

## Styleguides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line
* Consider starting the commit message with an emoji:
  - 🎉 `:tada:` when adding a major feature
  - 🐛 `:bug:` when fixing a bug
  - 📝 `:memo:` when writing docs
  - ✨ `:sparkles:` when improving code
  - 🔒 `:lock:` when improving security

### Python Styleguide

* Follow PEP 8
* Use 4 spaces for indentation
* Use meaningful variable names
* Add docstrings to functions and classes
* Keep functions focused and DRY
* Use type hints where applicable

```python
def process_conversation(conversation_id: int, user_id: int) -> dict:
    """
    Process a conversation and return the result.
    
    Args:
        conversation_id: The ID of the conversation
        user_id: The ID of the user
        
    Returns:
        A dictionary containing the processed conversation data
    """
    # Implementation here
    pass
```

### Documentation Styleguide

* Use Markdown
* Reference code using backticks
* Include code examples where helpful
* Keep line length reasonable for readability

## Development Setup

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. Install development dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if available
   ```
5. Create a branch for your changes:
   ```bash
   git checkout -b feature/my-new-feature
   ```

## Testing

* Write tests for new functionality
* Ensure all tests pass before submitting a PR:
  ```bash
  python -m pytest
  ```
* Aim for good test coverage

## Additional Notes

### Issue and Pull Request Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention is needed
- `question` - Further information is requested
- `security` - Security-related issue

## Recognition

Contributors will be recognized in our CONTRIBUTORS.md file and in the GitHub repository. Thank you for your contributions! 🎉

---

Questions? Feel free to open a discussion or reach out to the maintainers.
