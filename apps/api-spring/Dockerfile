FROM maven:3.9.9-eclipse-temurin-17

WORKDIR /app

COPY apps/api-spring /app/apps/api-spring
COPY config /app/config

WORKDIR /app/apps/api-spring

EXPOSE 8000

CMD ["mvn", "spring-boot:run", "-Dspring-boot.run.jvmArguments=-Dserver.port=8000"]
