// VoyageAI · 강원 — 정적 데이터 (Streamlit database.py / gangwon_content.py 이식)
"use strict";

const SPOTS = [
  { name: "방태산 자연휴양림 숲길", region: "인제군", description: "울창한 숲길 산책·힐링", lat: 37.9188, lng: 128.3506, theme: "힐링" },
  { name: "만항재 은하수 전망지", region: "정선군", description: "밤하늘 별·드라이브 명소", lat: 37.2049, lng: 128.9162, theme: "야경" },
  { name: "삼척 덕풍계곡 비경길", region: "삼척시", description: "계곡 트레킹·물소리 산책", lat: 37.1126, lng: 129.0452, theme: "트레킹" },
  { name: "영월 청령포 고요 산책", region: "영월군", description: "강변·역사 산책", lat: 37.1822, lng: 128.4616, theme: "역사" },
  { name: "평창 백룡동굴 탐방", region: "평창군", description: "동굴 탐방 체험", lat: 37.3833, lng: 128.4055, theme: "체험" },
  { name: "양구 파로호 둘레길", region: "양구군", description: "호수 둘레 자전거·산책", lat: 38.1118, lng: 127.9898, theme: "자전거" },
  { name: "속초 설악산 국립공원", region: "속초시", description: "케이블카·단풍·트레킹", lat: 38.1702, lng: 128.4913, theme: "트레킹" },
  { name: "강릉 경포대·해변", region: "강릉시", description: "호수·해변 산책", lat: 37.8058, lng: 128.8962, theme: "힐링" },
  { name: "강릉 안목해변 커피거리", region: "강릉시", description: "카페·일몰 드라이브", lat: 37.77, lng: 128.934, theme: "힐링" },
  { name: "춘천 남이섬", region: "춘천시", description: "섬 산책·자전거·드라마거리", lat: 37.7906, lng: 128.4661, theme: "체험" },
  { name: "춘천 소양강 스카이워크", region: "춘천시", description: "강 전망·포토스팟", lat: 37.8762, lng: 127.7298, theme: "야경" },
  { name: "원주 치악산 케이블카", region: "원주시", description: "산악 전망·단풍", lat: 37.38, lng: 128.054, theme: "트레킹" },
  { name: "홍천 비내섭계곡", region: "홍천군", description: "계곡 피서·물놀이", lat: 37.696, lng: 127.685, theme: "힐링" },
  { name: "태백산 천제단", region: "태백시", description: "고산 일출·눈꽃", lat: 37.0953, lng: 129.0302, theme: "트레킹" },
  { name: "정선 레일바이크", region: "정선군", description: "레일바이크·산골 풍경", lat: 37.22, lng: 128.84, theme: "체험" },
  { name: "정선 하이원 리조트 전망", region: "정선군", description: "산악 리조트·드라이브", lat: 37.183, lng: 128.818, theme: "힐링" },
  { name: "동해 무릉계곡", region: "동해시", description: "계곡·폭포 산책", lat: 37.075, lng: 129.14, theme: "트레킹" },
  { name: "동해 무릉 건강숲", region: "동해시", description: "숲길 트레킹", lat: 37.09, lng: 129.12, theme: "트레킹" },
  { name: "삼척 케이블카·용화해수욕장", region: "삼척시", description: "해안 케이블카·해변", lat: 37.005, lng: 129.17, theme: "체험" },
  { name: "고성 통일전망대", region: "고성군", description: "전망·역사", lat: 38.505, lng: 128.41, theme: "역사" },
  { name: "양양 서피비치", region: "양양군", description: "서핑·해변", lat: 38.072, lng: 128.669, theme: "체험" },
  { name: "인제 원대리 자작나무숲", region: "인제군", description: "숲길 포토·힐링", lat: 38.155, lng: 128.21, theme: "힐링" },
  { name: "횡성 한우·둔내 온천", region: "횡성군", description: "먹거리·온천", lat: 37.49, lng: 127.99, theme: "체험" },
  { name: "화천 산천어축제 거리", region: "화천군", description: "겨울 축제·얼음낚시", lat: 38.106, lng: 127.708, theme: "체험" },
];

const GANGWON_CITIES = [
  { city: "원주", lat: 37.3422, lng: 127.9202 },
  { city: "춘천", lat: 37.8747, lng: 127.7342 },
  { city: "강릉", lat: 37.7519, lng: 129.2022 },
  { city: "동해", lat: 37.5247, lng: 129.1144 },
  { city: "속초", lat: 38.207, lng: 128.5918 },
  { city: "삼척", lat: 37.4498, lng: 129.1652 },
  { city: "홍천", lat: 37.697, lng: 127.8887 },
  { city: "태백", lat: 37.1641, lng: 128.9856 },
  { city: "정선", lat: 37.3807, lng: 128.6608 },
  { city: "평창", lat: 37.3705, lng: 128.39 },
];

const FESTIVALS = [
  { title: "평창 송어축제", period: "1~2월", place: "평창군" },
  { title: "화천 산천어축제", period: "1월", place: "화천군" },
  { title: "강릉 커피축제", period: "10월", place: "강릉시" },
  { title: "정선 아리랑제", period: "10월", place: "정선군" },
  { title: "춘천 막국수 닭갈비 축제", period: "10월", place: "춘천시" },
  { title: "속초 설악산 단풍제", period: "10월", place: "속초시" },
  { title: "삼척 비치 페스티벌", period: "7~8월", place: "삼척시" },
  { title: "원주 댄싱카니발", period: "9월", place: "원주시" },
];

const FESTIVAL_ICONS = ["🎪", "🎭", "🎶", "🐟", "☕", "🎿", "🌸", "🍁"];

const WEATHER_ICONS = {
  sunny: { icon: "☀", label: "맑음", bg: "linear-gradient(135deg,#FDE68A,#FBBF24)" },
  partly_cloudy: { icon: "◐", label: "구름 조금", bg: "linear-gradient(135deg,#BAE6FD,#7DD3FC)" },
  cloudy: { icon: "☁", label: "흐림", bg: "linear-gradient(135deg,#E2E8F0,#94A3B8)" },
  fog: { icon: "≡", label: "안개", bg: "linear-gradient(135deg,#CBD5E1,#94A3B8)" },
  rain: { icon: "☂", label: "비", bg: "linear-gradient(135deg,#93C5FD,#3B82F6)" },
  snow: { icon: "❄", label: "눈", bg: "linear-gradient(135deg,#E0F2FE,#BAE6FD)" },
  thunder: { icon: "⚡", label: "뇌우", bg: "linear-gradient(135deg,#C4B5FD,#7C3AED)" },
};

const THEME_BADGE = {
  "트레킹": { label: "NATURE", cls: "badge-nature" },
  "힐링": { label: "CALM", cls: "badge-calm" },
  "체험": { label: "EXPERIENCE", cls: "badge-experience" },
  "야경": { label: "NIGHT", cls: "badge-night" },
  "역사": { label: "CULTURE", cls: "badge-culture" },
  "자전거": { label: "DRIVE", cls: "badge-drive" },
};

const THEME_IMAGE = {
  "트레킹": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=640&h=340&fit=crop&q=80",
  "힐링": "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=640&h=340&fit=crop&q=80",
  "체험": "https://images.unsplash.com/photo-1520250497591-112f2f996a74?w=640&h=340&fit=crop&q=80",
  "야경": "https://images.unsplash.com/photo-1514565131-fce0801e5785?w=640&h=340&fit=crop&q=80",
  "역사": "https://images.unsplash.com/photo-1590736969955-71cc94901144?w=640&h=340&fit=crop&q=80",
  "자전거": "https://images.unsplash.com/photo-1541625602330-2277a4fbfad2?w=640&h=340&fit=crop&q=80",
};
const DEFAULT_IMAGE = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=640&h=340&fit=crop&q=80";

const REGION_INTRO =
  "강원도는 산·바다·계곡이 가까워 <b>당일·반나절 여행</b>에 잘 맞아요. AI가 전역 관광지 중에서 취향에 맞는 동선을 골라 드립니다.";

const SUGGESTIONS = [
  { label: "강릉 카페 코스", prompt: "강릉 해안 드라이브와 분위기 좋은 카페가 있는 코스" },
  { label: "일몰 명소", prompt: "강원도 동해안 일몰 명소를 도는 반나절 코스" },
  { label: "가족 여행", prompt: "주차가 편하고 아이와 함께 가기 좋은 강원도 가족 코스" },
  { label: "단풍 트레킹", prompt: "설악산 단풍을 즐기는 가벼운 트레킹 코스" },
];

// Kakao JavaScript 키 — 도메인 제한으로 보호됨 (Kakao Developers에 도메인 등록 필요)
const KAKAO_JS_KEY = "6536ce6f37100f42b2fc1ba35203fb52";
