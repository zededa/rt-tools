FROM eci-base:latest

RUN apt-get update && apt-get install -y --allow-downgrades eci-realtime-benchmarking
RUN chmod +x /opt/benchmarking/mega-benchmark/48_hour_benchmark.sh

CMD ["/opt/benchmarking/mega-benchmark/48_hour_benchmark.sh"]