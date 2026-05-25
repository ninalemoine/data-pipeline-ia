# run pipeline every 30 minutes — stdout redirected to Docker log system
*/30 * * * * python3 /app/main.py >> /proc/1/fd/1 2>&1

