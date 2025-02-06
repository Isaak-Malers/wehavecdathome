# wehavecdathome

Continuous Deliver can get so complicated these days... Do you ever wish you could just.... ```docker compose up``` in ~~production~~ shared test environments?

That is EXACTLY what this project is intended to do.

It should enable you to spin up CD for integration, develop, or even random feature branches in less than 5 minutes.

It is the fastest way to cross of those "Set up Continuous Delivery for X Feature for Cross-Functional Teams" Jira tickets off.

### 0. Install wehavecdathome

```commandline
pip install wehavecdathome
```
install this pip package to get started.


### 1. Enter the Interactive Configuration Utility:

```commandline
wehavecdathome -s
```
This command will walk you through building a configuration file and host directory.

### 2. Test  GIT integration

```commandline
wehavecdathome -p
```

This Command will pull the configured GIT repository, and make sure permissions are set up correctly.

### 3. Test that your application starts up correctly

```commandline
wehavecdathome -t
```

This command will boot your application up so that you can test that everything is working correctly.

### 4. Host your Application
```commandline
wehavecdathome -h
```
This command will continuously monitor your repo, if it sees updates, it will pull them and re-deploy your application.

