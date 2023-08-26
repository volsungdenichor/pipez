[
        begin
        [persons := [|
            [{
                "first_name" "Adam"
                "last_name" "Mickiewicz"
                "birth" 1798
                "death" 1855
            }]
            [{
                "first_name" "Adam"
                "last_name" "Hanuszkiewicz"
                "birth" 1924
                "death" 2011
            }]
            [{
                "first_name" "Juliusz"
                "last_name" "Słowacki"
                "birth" 1809
                "death" 1849
            }]
            [{
                "first_name" "Adam"
                "last_name" "Bahdaj"
                "birth" 1918
                "death" 1985
            }]
            [{
                "first_name" "Adam"
                "last_name" "Małysz"
                "birth" 1977
            }]
            [{
                "first_name" "Adam"
                "last_name" "Baumann"
                "birth" 1948
                "death" 2021
            }]
        |]
        ]

       [age := [[p] -> [- [if [in p "death"] [@ p "death"] 2023] [@ p "birth"]] ]]

       [persons
           |> [ seq.filter [and [| [ age >> [ < 60 ] ] [ [ @ "first_name" ] >> [ == "Adam" ] ] |] ] ]
           |> [ seq.map [ ap age [ @ "last_name" ] [ @ "first_name" ] ] ]
       ]
]