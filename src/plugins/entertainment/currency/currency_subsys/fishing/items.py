class FishingRod:
    all_rod = {
        "name": ["竹竿","碳素杆","竞技杆","凌辉神竿"],
        "price": ["basic_fishing_rod","intermediate_fishing_rod","advanced_fishing_rod","maximal_fishing_rod"]
    }
    basic_fishing_rod = {
        "level":1,
        "name":"竹竿",
        "price":0,
        "bonus_min":5,
        "bonus_max":10
    }
    intermediate_fishing_rod = {
        "level":2,
        "name":"碳素杆",
        "price":500,
        "bonus_min":12,
        "bonus_max":20
    }
    advanced_fishing_rod = {
        "level":3,
        "name":"竞技杆",
        "price":2000,
        "bonus_min":22,
        "bonus_max":32
    }
    maximal_fishing_rod = {
        "level":4,
        "name":"凌辉神竿",
        "price":20000,
        "bonus_min":40,
        "bonus_max":50
    }

class FishingHook:
    all_hook = {
        "name": ["铁钩", "银钩", "金钩", "幸运钩"],
        "price": ["basic_fishhook", "intermediate_fishhook", "advanced_fishhook", "maximal_fishhook"]
    }
    basic_fishhook = {
        "level":1,
        "name":"铁钩",
        "price":80,
        "durability":100,
        "bonus":0
    }
    intermediate_fishhook = {
        "level":2,
        "name":"银钩",
        "price":300,
        "durability":200,
        "bonus":5
    }
    advanced_fishhook = {
        "level":3,
        "name":"金钩",
        "price":800,
        "durability":500,
        "bonus":10
    }
    maximal_fishhook = {
        "level":4,
        "name":"幸运钩",
        "price":2000,
        "durability":5,
        "bonus":50
    }

class FishingBait:
    basic_fishing_bait = {
        "level":1,
        "name":"普通饵料",
        "price":10,
        "bonus":0
    }
    intermediate_fishing_bait = {
        "level":2,
        "name":"初级饵料",
        "price":50,
        "bonus":5
    }
    advanced_fishing_bait = {
        "level":3,
        "name":"中级饵料",
        "price":200,
        "bonus":15
    }
    maximal_fishing_bait = {
        "level":4,
        "name":"高级饵料",
        "price":1000,
        "bonus":30
    }

class Fish:
    trash = {
        "bonus":40,
        "price":0
    }
    basic_fish = {
        "bonus":40,
        "price":30
    }
    intermediate_fish = {
        "bonus":15,
        "price":150
    }
    advanced_fish = {
        "bonus":5,
        "price":800
    }