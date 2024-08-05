##################
# Initialization
##################

# -- Project name 
project_name  = iclr2024_conference
public_name = llm_auction

# -- Timestamp
ts := $(shell /bin/date "+%Y-%m-%d---%H-%M-%S")


# -- Get and install packages
# package_list.txt:
# 	 find ../analysis/ -name *R -print0 | xargs -0 grep -h 'library*' | sed 's/library//g' | sed 's/#//g' | sed 's/ //g' | sort | uniq| sed 's/(//g' | sed 's/)//g' > package_list.txt
# install_packages: package_list.txt
# 	cat package_list.txt | xargs -I {} Rscript -e 'install.packages("{}", repos = "http://cran.us.r-project.org")'

# add_data: /home/john/Downloads/data_coy.tar.gz 
# 	cp /home/john/Downloads/data_coy.tar.gz ../etl/

##################
# Data and objects
##################

## --- 1. data 

# --- 3. List of objects
params    =
plots     =
tables    = 

# plots += plots/mug_love_scm.tex
# plots/mug_love_scm.tex: ../analysis/mug_love.py ../data/mug_love/
# 	cd ../analysis && python mug_love.py

# plots += plots/mug_love_scm_interaction.tex
# plots/mug_love_scm_interaction.tex: ../analysis/mug_love_interact.py ../data/mug_love/
# 	cd ../analysis && python mug_love_interact.py

# plots += plots/tax_fraud_scm.tex
# plots/tax_fraud_scm.tex: ../analysis/tax_fraud.py ../data/tax_fraud/
# 	cd ../analysis && python tax_fraud.py

# plots += plots/tax_fraud_scm_interaction.tex
# plots/tax_fraud_scm_interaction.tex: ../analysis/tax_fraud_interact.py ../data/tax_fraud/
# 	cd ../analysis && python tax_fraud_interact.py

# plots += plots/auction_art_3vars_scm.tex
# plots/auction_art_3vars_scm.tex: ../analysis/auction_art_3vars.py ../data/auction_art_3vars/
# 	cd ../analysis && python auction_art_3vars.py

# plots += plots/auction_art_3vars_scm_interaction.tex
# plots/auction_art_3vars_scm_interaction.tex: ../analysis/auction_art_3vars_interact.py ../data/auction_art_3vars/
# 	cd ../analysis && python auction_art_3vars_interact.py

# plots += plots/lawyer_interview_3var_scm.tex
# plots/lawyer_interview_3var_scm.tex: ../analysis/lawyer_interview_3var.py ../data/lawyer_interview_3var/
# 	cd ../analysis && python lawyer_interview_3var.py

# plots += plots/lawyer_interview_3var_scm_interaction.tex
# plots/lawyer_interview_3var_scm_interaction.tex: ../analysis/lawyer_interview_3var_interact.py ../data/lawyer_interview_3var/
# 	cd ../analysis && python lawyer_interview_3var_interact.py

# tables += tables/predictions_table.tex
# tables/predictions_table.tex: ../analysis/predictions_table.R ../data/
# 	cd ../analysis && Rscript predictions_table.R


##################
# 0. Preprocessing
##################



# --- plot
# plots += ./plots/availability_changes.pdf
# ./plots/availability_changes.pdf: ../computed_objects/availability_changes.csv ../analysis/availability_changes.R $(input)
# 	cd ../analysis && Rscript availability_changes.R

# tables += tables/summary_stats_impressions.tex
# tables/summary_stats_impressions.tex: ../analysis/summary_stats_impressions.R ../computed_objects/exp_effects_impression.csv ../analysis/summary_stats.R  ../analysis/pretty_names.R
# 	cd ../analysis && Rscript summary_stats_impressions.R

##################
# 6. Parameters
##################

# # ~~~~~~~~~~ 6.1 compute parameters
# # --- compute
# parameters += ./parameters/parameters.tex
# ./parameters/parameters.tex: ../analysis/parameters_compute.R $(input) $(input_experiment) $(client_allocations) $(client_posts) $(freelancer_allocations) $(freelancer_badge) ../computed_objects/availability_changes.csv ../computed_objects/availability_distribution.csv ../computed_objects/availability_invite_probability.csv ../computed_objects/exp_effects_cross.rds ../computed_objects/badge_in_search.csv ../computed_objects/badge_adoption_over_time.csv ../computed_objects/adopter_characteristics.csv
# 	cd ../analysis && Rscript parameters_compute.R


## --- M.1 Makes or updates manuscript using latex & bibtext
$(project_name).pdf: $(project_name).bib $(project_name).tex $(plots) $(tables) $(parameters) $(did_posts)
	pdflatex -interaction=batchmode $(project_name)
	bibtex $(project_name)
	pdflatex -interaction=batchmode $(project_name)
	pdflatex -interaction=batchmode $(project_name)


# website: $(project_name).pdf
# 	scp $(project_name).pdf johnjhorton@johnjhorton.ssh.wpengine.net:/home/wpe-user/sites/johnjhorton/papers/$(public_name).pdf


## --- M.2 Makes paper from scratch
clean:
	rm -f ../data/*.csv
	rm -f plots/*.png
	rm -f plots/*.pdf
	rm -f tables/*.tex
	rm -f parameters/*.tex
	rm -f ../computed_objects/*.csv
	rm -f ../computed_objects/*.rds
	rm -f $(project_name).pdf
	rm -f $(project_name).aux
	rm -f $(project_name).bbl
	rm -f $(project_name).blg
	rm -f $(project_name).log
	rm -f $(project_name).out
	make $(project_name).pdf

## --- M.3 Puts project on JJHs dropbox
toread: $(project_name).pdf
	cp $(project_name).pdf ~/Dropbox/toread/$(project_name)_$(ts).pdf
