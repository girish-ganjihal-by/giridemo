properties(
    [
        pipelineTriggers([[$class: 'PeriodicFolderTrigger', interval: '5m']])
    ]
)

@Library('centralJenkins@v4.2.0') _
central {
    nodes = [
        ["Debian_9", "python3.8"]
    ]
    docs = true
    flake8 = true
    black = true
    isort = true
    mypy = true
    ossaudit = true
    channel_name = "data_eng_jenkins"
    trigger_cron = "@daily"

    pipeline = "base_pipeline"
}
