python -m alembic upgrade head
cd src
python -m arq notifications.WorkerSettings &
python -m main
# Wait for any process to exit
wait -n
# Exit with status of process that exited first
exit $?