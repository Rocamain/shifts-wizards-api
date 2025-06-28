from invoke import task

# To use these tasks, install Invoke:
# pip install invoke

@task
def build(c):
    """Build the Docker image for Shift Wizard API"""
    c.run("docker build -t shift-wizard-api .", pty=True)

@task
def run(c):
    """Run the Docker container locally with environment variables from .env"""
    c.run("docker run --rm --env-file .env -p 5000:5000 shift-wizard-api", pty=True)

@task
def stop(c):
    """Stop the running Shift Wizard API container"""
    # Stops any container based on our image
    c.run(
        "docker ps -q --filter ancestor=shift-wizard-api | xargs -r docker stop",
        pty=True
    )

@task
def deploy(c, app_name="shifts-wizards-api"):
    """Deploy the app to Fly.io using flyctl"""
    c.run(f"flyctl deploy -a {app_name}", pty=True)
