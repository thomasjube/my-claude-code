# demo

Projet Maven basé sur **Spring Boot 4.1.1** (dernière version stable) et **Java 21**.

## Prérequis

- JDK 21+
- Maven 3.9+ (ou utiliser le wrapper `./mvnw` fourni)

## Commandes

```bash
./mvnw verify            # compile + tests + package
./mvnw spring-boot:run   # lance l'application
```

## Endpoints

- `GET /hello?name=Thomas` → `Hello, Thomas!`
- `GET /actuator/health` → état de l'application
