pub const TAG_PALETTE: [&str; 32] = [
    "#fc5c66", "#ea3b5a", "#99132a", "#fc9644", "#fb8231", "#a44b11", "#fed32f", "#f7b731",
    "#a07210", "#26dd81", "#20bf6b", "#0a7c40", "#2acbb9", "#0fb8b1", "#057873", "#45aaf2",
    "#2d99da", "#105e8d", "#4c7bed", "#3868d6", "#13378b", "#a55eea", "#8854d0", "#4a148c",
    "#d878e6", "#bd4acc", "#781884", "#a5b0c2", "#778ba2", "#4b6684", "#a0887e", "#795547",
];

pub const NO_COLOR: &str = "";

pub fn is_valid_tag_color(color: &str) -> bool {
    color.is_empty() || TAG_PALETTE.contains(&color)
}
