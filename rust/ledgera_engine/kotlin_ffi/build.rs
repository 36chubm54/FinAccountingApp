fn main() {
    uniffi::generate_scaffolding("src/ledgera_engine.udl")
        .expect("failed to generate UniFFI scaffolding");
}
